from __future__ import annotations

import logging

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPropertyAnimation,
    QSignalBlocker,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFontMetrics
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.core.models import Status, Task
from task_manager_desktop.core.sector import PERMANENT_ACCENT, count_open_deps
from task_manager_desktop.ui.icons import (
    CLOCK_SVG,
    COIN_FILLED_SVG,
    COIN_OUTLINE_SVG,
    PENCIL_WHITE_SVG,
    STAR_FILLED_SVG,
    STAR_OUTLINE_SVG,
    STRATEGY_SVG,
    TRASH_SVG,
    svg_to_icon,
)
from task_manager_desktop.ui.widgets.status_segmented_control import (
    CONTROL_HEIGHT as _STATUS_HEIGHT,
)
from task_manager_desktop.ui.widgets.status_segmented_control import (
    CONTROL_WIDTH as _STATUS_WIDTH,
)
from task_manager_desktop.ui.widgets.status_segmented_control import (
    StatusSegmentedControl,
)

# CL-073: INTAKE diz "card verde #16a34a"; mantemos bg #14532D + accent #16A34A para garantir contraste WCAG do texto. Hex de referencia preservado como accent.
_CARD_STYLE: dict[str, dict[str, str]] = {
    "active": {
        "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #166534, stop:1 #0F3F24)",
        "hover": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #15803D, stop:1 #14532D)",
        "accent": "#16A34A",
        "title": "#ECFDF5",
        "meta": "#BBF7D0",
        "chip_bg": "rgba(5, 46, 22, 0.55)",
        "chip_text": "#DCFCE7",
        "deps": "#BBF7D0",
    },
    "preparing": {
        # Tom verde claro: a task aguarda sua estrategia ser escrita antes de
        # ir para "Em execução". Texto escuro para contraste WCAG sobre claro.
        "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #86EFAC, stop:1 #4ADE80)",
        "hover": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #BBF7D0, stop:1 #86EFAC)",
        "accent": "#16A34A",
        "title": "#0B3D20",
        "meta": "#14532D",
        "chip_bg": "rgba(20, 83, 45, 0.16)",
        "chip_text": "#14532D",
        "deps": "#14532D",
    },
    "waiting": {
        "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FACC15, stop:1 #D97706)",
        "hover": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FDE047, stop:1 #EAB308)",
        "accent": "#FEF08A",
        "title": "#18181B",
        "meta": "#3F2D00",
        "chip_bg": "rgba(24, 24, 27, 0.18)",
        "chip_text": "#18181B",
        "deps": "#3F2D00",
    },
    "blocked": {
        "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #52525B, stop:1 #34343B)",
        "hover": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #62626D, stop:1 #3F3F46)",
        "accent": "#A1A1AA",
        "title": "#F4F4F5",
        "meta": "#D4D4D8",
        "chip_bg": "rgba(24, 24, 27, 0.42)",
        "chip_text": "#F4F4F5",
        "deps": "#EAB308",
    },
    "done": {
        "bg": "#18181B",
        "hover": "#242427",
        "accent": "#52525B",
        "title": "#8B8F9B",
        "meta": "#686C78",
        "chip_bg": "rgba(63, 63, 70, 0.4)",
        "chip_text": "#A1A1AA",
        "deps": "#686C78",
    },
}


_log = logging.getLogger(__name__)

# Janela de debounce do autosave da estrela favorito (source.md AC-14): cliques
# rapidos sucessivos colapsam num unico autosave.
_FAVORITO_DEBOUNCE_MS = 250
# Opacidade do icone da estrela enquanto o autosave esta pendente (sinal visual).
_STAR_PENDING_OPACITY = 0.4
# Watchdog do lockout in-flight da estrela (source.md secao 9): se o callback de
# autosave nunca resolver (UI-thread travada, lock no SQLite), a estrela ficaria
# desabilitada para sempre. Decorrido este prazo sem resolucao, o watchdog forca
# rollback ao valor persistido, re-habilita a estrela e loga um erro explicito.
_STAR_IN_FLIGHT_WATCHDOG_MS = 5000


class TaskCard(QFrame):
    selected = Signal(object)

    def __init__(
        self,
        task: Task,
        callbacks: dict,
        all_tasks: list[Task],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._task = task
        self._callbacks = callbacks
        self._all_tasks_list = all_tasks
        self._all_tasks: dict[str, Task] = {t.id: t for t in all_tasks}
        self._selected = False

        # Estado do autosave debounced da estrela favorito (source.md AC-14).
        # `_fav_pending_value` guarda o valor que o usuario pediu; `_fav_syncing`
        # bloqueia reentrancia quando o rollback reverte o checked programaticamente;
        # `_fav_in_flight` marca que o request ja foi despachado (debounce disparou)
        # e a estrela esta travada ate o request resolver (source.md AC-14).
        self._fav_pending_value = task.favorito
        self._fav_syncing = False
        self._fav_in_flight = False
        self._fav_debounce = QTimer(self)
        self._fav_debounce.setSingleShot(True)
        self._fav_debounce.setInterval(_FAVORITO_DEBOUNCE_MS)
        self._fav_debounce.timeout.connect(self._on_favorite_debounce_fired)
        # Watchdog do lockout in-flight (source.md secao 9): armado quando o
        # request e despachado; se disparar antes do request resolver, forca
        # rollback + re-enable para a estrela nao ficar travada indefinidamente.
        self._fav_watchdog = QTimer(self)
        self._fav_watchdog.setSingleShot(True)
        self._fav_watchdog.setInterval(_STAR_IN_FLIGHT_WATCHDOG_MS)
        self._fav_watchdog.timeout.connect(self._on_favorite_watchdog_fired)
        self._coin_pending_value = bool(
            self._callbacks.get("is_coin_favorite", lambda _tid: False)(task.id)
        )
        self._coin_syncing = False
        self._coin_in_flight = False
        self._coin_debounce = QTimer(self)
        self._coin_debounce.setSingleShot(True)
        self._coin_debounce.setInterval(_FAVORITO_DEBOUNCE_MS)
        self._coin_debounce.timeout.connect(self._on_coin_debounce_fired)
        self._coin_watchdog = QTimer(self)
        self._coin_watchdog.setSingleShot(True)
        self._coin_watchdog.setInterval(_STAR_IN_FLIGHT_WATCHDOG_MS)
        self._coin_watchdog.timeout.connect(self._on_coin_watchdog_fired)

        self.setObjectName("taskCard")
        self.setProperty("testid", f"task-card-{task.id}")
        self.setFixedHeight(_STATUS_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setProperty("selected", False)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setAccessibleName(f"Task {task.id}")
        self.setAccessibleDescription(f"{task.title}, {task.status.value}")

        self._has_active_schedule: bool = False
        self._build_ui()
        self._apply_card_style()

    def _card_state(self) -> str:
        open_deps = count_open_deps(self._task.deps, self._all_tasks)
        if self._task.status == Status.DONE:
            return "done"
        # Flag manual tem prioridade sobre blocked/active/waiting (espelha
        # compute_sector), mas nunca sobre done.
        if getattr(self._task, "em_preparacao", False):
            return "preparing"
        if open_deps > 0:
            return "blocked"
        if self._task.status == Status.IN_PROGRESS:
            return "active"
        return "waiting"

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Coluna de conteudo — 2 linhas: meta (icone + id + deps) e titulo.
        self._content_col = QWidget(self)
        self._content_col.setObjectName("taskCardContentColumn")
        self._content_col.setProperty("testid", f"task-card-{self._task.id}-content")
        self._content_col.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._content_col.setStyleSheet("background: transparent;")
        outer = QVBoxLayout(self._content_col)
        outer.setContentsMargins(9, 5, 6, 5)
        outer.setSpacing(2)
        root.addWidget(self._content_col, 95)

        # Linha 1 (meta): icone de tipo, ID, deps e acoes hover.
        self._top_row = QWidget(self._content_col)
        self._top_row.setObjectName("taskCardTopRow")
        top_row = QHBoxLayout(self._top_row)
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(5)

        # Linha 2 (titulo).
        self._middle_row = QWidget(self._content_col)
        self._middle_row.setObjectName("taskCardMiddleRow")
        middle_row = QHBoxLayout(self._middle_row)
        middle_row.setContentsMargins(0, 0, 0, 0)
        middle_row.setSpacing(0)

        outer.addWidget(self._top_row, 0)
        outer.addWidget(self._middle_row, 1)

        # Estrela de favorito — primeira posicao da primeira linha. Checkable
        # com autosave debounced; o estado inicial e aplicado ANTES de conectar
        # `toggled` para nao disparar autosave so pela renderizacao.
        self._star_btn = QToolButton(self._top_row)
        self._star_btn.setObjectName("cardFavoriteStar")
        self._star_btn.setProperty("testid", f"task-card-{self._task.id}-favorito")
        self._star_btn.setCheckable(True)
        self._star_btn.setChecked(self._task.favorito)
        self._star_btn.setIconSize(QSize(16, 16))
        self._star_btn.setFixedSize(20, 20)
        self._star_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._star_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._star_btn.setAccessibleName("Marcar como favorito")
        self._star_btn.setStyleSheet(
            "QToolButton#cardFavoriteStar {"
            "background: transparent; border: none; padding: 0;"
            "}"
            "QToolButton#cardFavoriteStar:focus {"
            "border: 1px solid rgba(255,255,255,0.55); border-radius: 6px;"
            "}"
        )
        # Efeito de opacidade reutilizado para sinalizar o estado "pending".
        self._star_opacity = QGraphicsOpacityEffect(self._star_btn)
        self._star_opacity.setOpacity(1.0)
        self._star_btn.setGraphicsEffect(self._star_opacity)
        self._star_btn.toggled.connect(self._on_star_toggled)
        top_row.addWidget(self._star_btn)
        self._refresh_star_icon()
        self._set_star_pending(False)

        self._coin_btn = QToolButton(self._top_row)
        self._coin_btn.setObjectName("cardFavoriteCoin")
        self._coin_btn.setProperty("testid", f"task-card-{self._task.id}-favorito-moeda")
        self._coin_btn.setCheckable(True)
        self._coin_btn.setChecked(self._coin_pending_value)
        self._coin_btn.setIconSize(QSize(16, 16))
        self._coin_btn.setFixedSize(20, 20)
        self._coin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._coin_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._coin_btn.setAccessibleName("Marcar moeda favorita")
        self._coin_btn.setStyleSheet(
            "QToolButton#cardFavoriteCoin {"
            "background: transparent; border: none; padding: 0;"
            "}"
            "QToolButton#cardFavoriteCoin:focus {"
            "border: 1px solid rgba(255,255,255,0.55); border-radius: 6px;"
            "}"
        )
        self._coin_opacity = QGraphicsOpacityEffect(self._coin_btn)
        self._coin_opacity.setOpacity(1.0)
        self._coin_btn.setGraphicsEffect(self._coin_opacity)
        self._coin_btn.toggled.connect(self._on_coin_toggled)
        top_row.addWidget(self._coin_btn)
        self._refresh_coin_icon()
        self._set_coin_pending(False)

        # O card principal NAO exibe mais o tipo (agent/dev/human): esse marcador
        # passou a viver nas subtasks (cada task tem partes de tipos distintos).
        # O filtro header-type-filter agora atua via a existencia de subtasks do
        # tipo selecionado, nao via um tipo unico da task.

        self._id_label = QLabel(f"#{self._task.id}", self)
        self._id_label.setObjectName("cardId")
        self._id_label.setProperty("testid", f"task-card-{self._task.id}-id")
        top_row.addWidget(self._id_label)

        self._deps_label = QLabel(self)
        self._deps_label.setObjectName("cardDeps")
        self._deps_label.setProperty("testid", f"task-card-{self._task.id}-deps")
        self._deps_label.setTextFormat(Qt.TextFormat.PlainText)
        # Permite encolher quando a coluna 1 ficar estreita, evitando overflow horizontal do card.
        self._deps_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self._deps_label.setMinimumWidth(0)
        top_row.addWidget(self._deps_label)
        top_row.addStretch()

        self._actions_row = QWidget(self)
        self._actions_row.setObjectName("cardHoverActions")
        self._actions_row.setProperty("testid", f"task-card-{self._task.id}-actions")
        actions_layout = QHBoxLayout(self._actions_row)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(4)
        top_row.addWidget(self._actions_row, 0, Qt.AlignmentFlag.AlignRight)

        self._edit_btn = QToolButton(self._actions_row)
        self._edit_btn.setObjectName("cardActionEdit")
        self._edit_btn.setProperty("testid", f"task-card-{self._task.id}-edit")
        self._edit_btn.setIcon(svg_to_icon(PENCIL_WHITE_SVG, 16))
        self._edit_btn.setIconSize(QSize(16, 16))
        self._edit_btn.setFixedSize(22, 22)
        self._edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._edit_btn.setAccessibleName(f"Editar task {self._task.id}")
        self._edit_btn.clicked.connect(self._handle_edit)
        actions_layout.addWidget(self._edit_btn)

        self._schedule_btn = QToolButton(self._actions_row)
        self._schedule_btn.setObjectName("cardActionSchedule")
        self._schedule_btn.setProperty("testid", f"task-card-{self._task.id}-schedule")
        self._schedule_btn.setIcon(svg_to_icon(CLOCK_SVG, 16))
        self._schedule_btn.setIconSize(QSize(16, 16))
        self._schedule_btn.setFixedSize(22, 22)
        self._schedule_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._schedule_btn.setAccessibleName(f"Agendar task permanente {self._task.id}")
        self._schedule_btn.setToolTip("Agendar acompanhamento")
        self._schedule_btn.setVisible(self._task.permanente)
        self._schedule_btn.clicked.connect(self._handle_schedule)
        actions_layout.addWidget(self._schedule_btn)

        # Botao "Em preparação" — ao lado do schedule. Move o card para o setor
        # verde claro enquanto sua estrategia e escrita. Icone 1:1 (16x16).
        self._prepare_btn = QToolButton(self._actions_row)
        self._prepare_btn.setObjectName("cardActionPrepare")
        self._prepare_btn.setProperty("testid", f"task-card-{self._task.id}-prepare")
        self._prepare_btn.setIcon(svg_to_icon(STRATEGY_SVG, 16))
        self._prepare_btn.setIconSize(QSize(16, 16))
        self._prepare_btn.setFixedSize(22, 22)
        self._prepare_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._prepare_btn.setAccessibleName(f"Mover task {self._task.id} para Em preparação")
        self._prepare_btn.setToolTip("Mover para Em preparação")
        self._prepare_btn.setVisible(self._prepare_allowed())
        self._prepare_btn.clicked.connect(self._handle_prepare)
        actions_layout.addWidget(self._prepare_btn)

        self._delete_btn = QToolButton(self._actions_row)
        self._delete_btn.setObjectName("cardActionDelete")
        self._delete_btn.setProperty("testid", f"task-card-{self._task.id}-delete")
        self._delete_btn.setIcon(svg_to_icon(TRASH_SVG, 16))
        self._delete_btn.setIconSize(QSize(16, 16))
        self._delete_btn.setFixedSize(22, 22)
        self._delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_btn.setAccessibleName(f"Excluir task {self._task.id}")
        self._delete_btn.clicked.connect(self._handle_delete)
        actions_layout.addWidget(self._delete_btn)

        # Titulo (linha 2).
        self._title_label = QLabel(self._task.title, self)
        self._title_label.setObjectName("cardTitle")
        self._title_label.setProperty("testid", f"task-card-{self._task.id}-title")
        self._title_label.setTextFormat(Qt.TextFormat.PlainText)
        self._title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._title_label.setToolTip(self._task.title)
        self._title_label.mouseDoubleClickEvent = lambda _e: self._begin_inline_edit()
        middle_row.addWidget(self._title_label)

        # Edicao inline do titulo — visivel apenas durante o double-click edit.
        self._title_edit = QLineEdit(self._task.title, self)
        self._title_edit.setObjectName("cardTitleEdit")
        self._title_edit.setProperty("testid", f"task-card-{self._task.id}-title-edit")
        self._title_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._title_edit.installEventFilter(self)
        self._title_edit.editingFinished.connect(self._commit_inline_edit)
        self._title_edit.hide()
        middle_row.addWidget(self._title_edit)

        # Coluna de status — colada na borda direita, altura total do card.
        self._status_col = QWidget(self)
        self._status_col.setObjectName("taskCardStatusColumn")
        self._status_col.setProperty("testid", f"task-card-{self._task.id}-status-column")
        self._status_col.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._status_col.setStyleSheet("background: transparent;")
        self._status_col.setFixedWidth(_STATUS_WIDTH)
        right_rail = QVBoxLayout(self._status_col)
        right_rail.setContentsMargins(0, 0, 0, 0)
        right_rail.setSpacing(0)

        self._seg_ctrl = StatusSegmentedControl(self._task, self._all_tasks, self)
        self._seg_ctrl.status_changed.connect(self._on_status_change)
        right_rail.addWidget(self._seg_ctrl)
        root.addWidget(self._status_col, 5)

        # Alias legado para testes/metodos antigos. Nao e renderizado no card.
        self._menu_btn = QPushButton("", self)
        self._menu_btn.setProperty("testid", f"task-card-{self._task.id}-menu")
        self._menu_btn.setVisible(False)

        self._refresh_text_content()
        self._set_hover_actions_visible(False)

    def _refresh_text_content(self) -> None:
        fm = QFontMetrics(self.font())
        self._title_label.setText(self._task.title)
        self._title_label.setToolTip(self._task.title)

        if self._task.deps:
            deps_text = "deps: " + ", ".join(self._task.deps)
            self._deps_label.setText(fm.elidedText(deps_text, Qt.TextElideMode.ElideRight, 120))
            self._deps_label.setToolTip(deps_text)
            self._deps_label.show()
        else:
            self._deps_label.setText("")
            self._deps_label.setToolTip("")
            self._deps_label.hide()

    # ------------------------------------------------------------------
    # Estrela de favorito (autosave debounced — source.md secao 3.6 / AC-14)
    # ------------------------------------------------------------------

    def _refresh_star_icon(self) -> None:
        """Sincroniza icone e descricao acessivel da estrela com o checked atual."""
        checked = self._star_btn.isChecked()
        svg = STAR_FILLED_SVG if checked else STAR_OUTLINE_SVG
        self._star_btn.setIcon(svg_to_icon(svg, 16))
        self._star_btn.setAccessibleDescription("Favorita" if checked else "Não favorita")

    def _set_star_pending(self, pending: bool) -> None:
        """Estado visual do autosave: opacidade reduzida + tooltip enquanto pendente."""
        self._star_opacity.setOpacity(_STAR_PENDING_OPACITY if pending else 1.0)
        self._star_btn.setToolTip(
            "Salvando favorito..." if pending else "Favoritar task"
        )

    def _set_star_in_flight(self, in_flight: bool) -> None:
        """Trava/destrava a interacao da estrela enquanto o request esta no ar.

        source.md AC-14: a estrela em estado pending durante o autosave nao
        aceita novo toggle. A janela de debounce de 250 ms ANTES do request
        ainda colapsa cliques rapidos (ultimo valor vence); somente depois
        que o debounce dispara e o request e despachado a estrela e travada,
        ate o request resolver (sucesso ou rollback).
        """
        self._fav_in_flight = in_flight
        # setEnabled(False) recusa cliques/teclado; reabilitado no resolve.
        self._star_btn.setEnabled(not in_flight)
        # Watchdog: armado junto com o lockout; parado quando o request resolve
        # (sucesso ou rollback) para nao disparar rollback espurio depois.
        if in_flight:
            self._fav_watchdog.start()
        else:
            self._fav_watchdog.stop()

    def _on_favorite_watchdog_fired(self) -> None:
        """Disparado quando o request in-flight nao resolve dentro do prazo.

        Cenario de falha silenciosa (source.md secao 9): o callback de autosave
        nunca retornou (UI-thread travada, lock prolongado no SQLite). Sem este
        watchdog a estrela ficaria desabilitada para sempre. Forca o rollback ao
        valor persistido, re-habilita a estrela e loga um erro explicito.
        """
        # Guard de idempotencia: se o request ja resolveu, o watchdog foi
        # parado; este metodo so executa enquanto ainda ha lockout ativo.
        if not self._fav_in_flight:
            return
        _log.error(
            "favorito.autosave_watchdog_timeout: request in-flight nao resolveu "
            "em %d ms; forcando rollback da estrela (task_id=%s)",
            _STAR_IN_FLIGHT_WATCHDOG_MS,
            self._task.id,
        )
        self._rollback_star()

    def _on_star_toggled(self, checked: bool) -> None:
        # Guard de reentrancia: o rollback usa QSignalBlocker, mas o guard
        # protege qualquer caminho futuro que altere o checked sem bloquear sinal.
        if self._fav_syncing:
            return
        # Lockout in-flight (source.md AC-14): se o request ja foi despachado,
        # nao aceita novo toggle ate resolver. O setEnabled(False) ja recusa
        # cliques, mas o guard protege caminhos programaticos.
        if self._fav_in_flight:
            return
        self._fav_pending_value = checked
        self._refresh_star_icon()
        self._set_star_pending(True)
        # Debounce: cliques rapidos sucessivos colapsam num unico autosave.
        self._fav_debounce.start()

    def _on_favorite_debounce_fired(self) -> None:
        # Request despachado: trava a estrela ate resolver (source.md AC-14).
        self._set_star_in_flight(True)
        cb = self._callbacks.get("on_favorite_toggle")
        if cb is None:
            # Sem callback conectado (ex.: card isolado em teste): nao ha como
            # persistir — reverte para o valor da task e sai do estado pending.
            self._rollback_star()
            return
        ok = cb(self._task, self._fav_pending_value)
        if ok:
            # Sucesso: o controller dispara task_list.refresh(), que destroi e
            # recria todos os cards. Este card esta agendado para deleteLater —
            # nao tocar em mais nada para evitar acesso a widget ja deletado.
            return
        # Falha: o refresh nao aconteceu e o card sobrevive. Rollback visual
        # para o estado persistido, sem autosave silencioso (source.md rejeicao #10).
        self._rollback_star()

    def _refresh_coin_icon(self) -> None:
        checked = self._coin_btn.isChecked()
        svg = COIN_FILLED_SVG if checked else COIN_OUTLINE_SVG
        self._coin_btn.setIcon(svg_to_icon(svg, 16))
        self._coin_btn.setAccessibleDescription("Moeda favorita" if checked else "Moeda não favorita")

    def _set_coin_pending(self, pending: bool) -> None:
        self._coin_opacity.setOpacity(_STAR_PENDING_OPACITY if pending else 1.0)
        self._coin_btn.setToolTip("Salvando moeda..." if pending else "Favoritar com moeda")

    def _set_coin_in_flight(self, in_flight: bool) -> None:
        self._coin_in_flight = in_flight
        self._coin_btn.setEnabled(not in_flight)
        if in_flight:
            self._coin_watchdog.start()
        else:
            self._coin_watchdog.stop()

    def _on_coin_watchdog_fired(self) -> None:
        if not self._coin_in_flight:
            return
        _log.error(
            "coin.autosave_watchdog_timeout: request in-flight nao resolveu "
            "em %d ms; forcando rollback da moeda (task_id=%s)",
            _STAR_IN_FLIGHT_WATCHDOG_MS,
            self._task.id,
        )
        self._rollback_coin()

    def _on_coin_toggled(self, checked: bool) -> None:
        if self._coin_syncing or self._coin_in_flight:
            return
        self._coin_pending_value = checked
        self._refresh_coin_icon()
        self._set_coin_pending(True)
        self._coin_debounce.start()

    def _on_coin_debounce_fired(self) -> None:
        self._set_coin_in_flight(True)
        cb = self._callbacks.get("on_coin_toggle")
        if cb is None:
            self._rollback_coin()
            return
        ok = cb(self._task, self._coin_pending_value)
        if ok:
            return
        self._rollback_coin()

    def _rollback_coin(self) -> None:
        self._coin_syncing = True
        try:
            persisted = bool(
                self._callbacks.get("is_coin_favorite", lambda _tid: False)(self._task.id)
            )
            with QSignalBlocker(self._coin_btn):
                self._coin_btn.setChecked(persisted)
        finally:
            self._coin_syncing = False
        self._coin_pending_value = self._coin_btn.isChecked()
        self._refresh_coin_icon()
        self._set_coin_pending(False)
        self._set_coin_in_flight(False)

    def _rollback_star(self) -> None:
        """Reverte a estrela ao valor persistido da task, sem disparar autosave."""
        self._fav_syncing = True
        try:
            with QSignalBlocker(self._star_btn):
                self._star_btn.setChecked(self._task.favorito)
        finally:
            self._fav_syncing = False
        self._fav_pending_value = self._task.favorito
        self._refresh_star_icon()
        self._set_star_pending(False)
        # Request resolveu (rollback/erro): destrava a estrela para novos
        # toggles e restaura o foco de teclado (source.md AC-14).
        self._set_star_in_flight(False)

    def _apply_card_style(self) -> None:
        state = self._card_state()
        style = _CARD_STYLE[state]
        selected_border = "border-left: 3px solid #FFFFFF;" if self._selected else ""
        # Task permanente: a marca fica APENAS no detalhe azul da borda
        # esquerda (7px). O contorno externo e o mesmo neutro das
        # demais tasks.
        outer_border = "border: 1px solid rgba(255,255,255,0.09);"
        if self._task.permanente:
            left_border = f"border-left: 7px solid {PERMANENT_ACCENT};"
        else:
            left_border = f"border-left: 7px solid {style['accent']};"
        _schedule_active_css = (
            "QToolButton#cardActionSchedule {"
            "background: rgba(251,191,36,0.22);"
            "border: 1px solid rgba(251,191,36,0.55);"
            "border-radius: 8px; padding: 2px;"
            "}"
            "QToolButton#cardActionSchedule:hover {"
            "background: rgba(251,191,36,0.42);"
            "border: 1px solid rgba(251,191,36,0.90);"
            "}"
        ) if self._has_active_schedule else (
            "QToolButton#cardActionSchedule {"
            "background: rgba(5,6,8,0.72);"
            "border: 1px solid rgba(255,255,255,0.18);"
            "border-radius: 8px; padding: 2px;"
            "}"
            "QToolButton#cardActionSchedule:hover {"
            "background: rgba(255,255,255,0.18);"
            "border: 1px solid rgba(255,255,255,0.42);"
            "}"
        )
        self.setStyleSheet(
            "QFrame#taskCard { /* legacy-border #3F3F46 */"
            f"background: {style['bg']};"
            f"{outer_border}"
            f"{left_border}"
            f"{selected_border}"
            "border-radius: 12px;"
            "}"
            "QFrame#taskCard:hover {"
            f"background: {style['hover']};"
            "}"
            "QToolButton#cardActionEdit, QToolButton#cardActionDelete, "
            "QToolButton#cardActionPrepare {"
            "background: rgba(5,6,8,0.72);"
            "border: 1px solid rgba(255,255,255,0.18);"
            "border-radius: 8px;"
            "padding: 2px;"
            "}"
            "QToolButton#cardActionEdit:hover, QToolButton#cardActionDelete:hover, "
            "QToolButton#cardActionPrepare:hover {"
            "background: rgba(255,255,255,0.18);"
            "border: 1px solid rgba(255,255,255,0.42);"
            "}"
            + _schedule_active_css
        )
        self._id_label.setStyleSheet(
            f"font-family: 'JetBrains Mono', 'Ubuntu Mono', monospace; font-size: 12px; "
            f"font-weight: 800; color: {style['meta']}; background: transparent; "
            "padding: 0;"
        )
        title_legacy_marker = " /* #A1A1AA */" if state == "blocked" else ""
        _title_css = (
            f"font-size: 12px; font-weight: 600; color: {style['title']}; "
            f"background: transparent;{title_legacy_marker}"
        )
        self._title_label.setStyleSheet(_title_css)
        self._title_edit.setStyleSheet(
            f"QLineEdit#cardTitleEdit {{"
            f"font-size: 12px; font-weight: 600; color: {style['title']};"
            f"background: transparent;"
            f"border: none; border-bottom: 1px solid rgba(255,255,255,0.35);"
            f"padding: 0; margin: 0;"
            f"}}"
        )
        open_deps = count_open_deps(self._task.deps, self._all_tasks)
        deps_color = "#EAB308" if open_deps > 0 else "#71717A"
        self._deps_label.setStyleSheet(
            f"font-family: 'JetBrains Mono', 'Ubuntu Mono', monospace; font-size: 11px; "
            f"font-weight: 700; color: {deps_color}; background: transparent;"
        )
        self._seg_ctrl.apply_palette(state, style)

    def _begin_inline_edit(self) -> None:
        self._title_edit.setText(self._task.title)
        self._title_label.hide()
        self._title_edit.show()
        self._title_edit.setFocus(Qt.FocusReason.MouseFocusReason)
        self._title_edit.selectAll()

    def _commit_inline_edit(self) -> None:
        if self._title_edit.isHidden():
            return
        new_title = self._title_edit.text().strip()
        self._title_edit.hide()
        self._title_label.show()
        if new_title and new_title != self._task.title:
            cb = self._callbacks.get("on_title_save")
            if cb:
                cb(self._task, new_title)

    def _cancel_inline_edit(self) -> None:
        self._title_edit.hide()
        self._title_label.show()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if watched is self._title_edit and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:  # type: ignore[attr-defined]
                self._cancel_inline_edit()
                return True
        return super().eventFilter(watched, event)

    def set_schedule_active(self, due_at: str | None) -> None:
        self._has_active_schedule = due_at is not None
        self._apply_card_style()
        if self._has_active_schedule and self._task.permanente:
            self._actions_row.setVisible(True)
            self._schedule_btn.setVisible(True)

    def _set_hover_actions_visible(self, visible: bool) -> None:
        if self._has_active_schedule and self._task.permanente:
            self._actions_row.setVisible(True)
            self._edit_btn.setVisible(visible)
            self._delete_btn.setVisible(visible)
            self._schedule_btn.setVisible(True)
            self._prepare_btn.setVisible(visible and self._prepare_allowed())
        else:
            self._actions_row.setVisible(visible)
            if visible:
                self._edit_btn.setVisible(True)
                self._delete_btn.setVisible(True)
                self._schedule_btn.setVisible(self._task.permanente)
                self._prepare_btn.setVisible(self._prepare_allowed())

    def _handle_edit(self) -> None:
        cb = self._callbacks.get("on_edit")
        if cb:
            cb(self._task)

    def _handle_delete(self) -> None:
        cb = self._callbacks.get("on_delete")
        if cb:
            cb(self._task)

    def _handle_schedule(self) -> None:
        cb = self._callbacks.get("on_schedule_permanent")
        if cb:
            cb(self._task)

    def _prepare_allowed(self) -> bool:
        """O botao "Em preparação" so faz sentido em tasks nao concluidas."""
        return self._task.status != Status.DONE

    def _handle_prepare(self) -> None:
        cb = self._callbacks.get("on_toggle_preparacao")
        if cb:
            cb(self._task)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.setProperty("selected", selected)
        self._apply_selected_glow(selected)
        self._apply_card_style()

    def _apply_selected_glow(self, selected: bool) -> None:
        """Halo branco no card selecionado (o que esta renderizando as subtasks).

        Alem da faixa branca a esquerda (border-left), o card selecionado ganha
        um QGraphicsDropShadowEffect branco com offset zero — um glow suave que
        o destaca dos demais. Removido ao deselecionar para nao acumular efeitos
        (um QWidget so comporta um QGraphicsEffect por vez).
        """
        if selected:
            glow = QGraphicsDropShadowEffect(self)
            glow.setBlurRadius(20)
            glow.setColor(QColor(255, 255, 255, 180))
            glow.setOffset(0, 0)
            self.setGraphicsEffect(glow)
        else:
            self.setGraphicsEffect(None)

    def _on_status_change(self, new_status: str) -> None:
        cb = self._callbacks.get("on_status_change")
        if cb:
            cb(self._task, new_status, self._seg_ctrl)

    def _show_context_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #202126; border: 1px solid #3f3f46; "
            "border-radius: 10px; padding: 6px; }"
            "QMenu::item { padding: 9px 18px; border-radius: 6px; color: #F8FAFC; }"
            "QMenu::item:selected { background: #373A43; }"
        )

        edit_action = menu.addAction("Editar")
        delete_action = menu.addAction("Excluir")

        pos = self._menu_btn.mapToGlobal(self._menu_btn.rect().bottomRight())
        action = menu.exec(pos)

        if action == edit_action:
            cb = self._callbacks.get("on_edit")
            if cb:
                cb(self._task)
        elif action == delete_action:
            cb = self._callbacks.get("on_delete")
            if cb:
                cb(self._task)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._set_hover_actions_visible(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._set_hover_actions_visible(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)
        self.selected.emit(self._task)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def pulse(self) -> QPropertyAnimation:
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(200)
        anim.setStartValue(0.6)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        return anim

    def update_task(self, task: Task, all_tasks: list[Task]) -> None:
        self._task = task
        self._all_tasks_list = all_tasks
        self._all_tasks = {t.id: t for t in all_tasks}
        self.setProperty("testid", f"task-card-{task.id}")
        self.setAccessibleName(f"Task {task.id}")
        self.setAccessibleDescription(f"{task.title}, {task.status.value}")
        self._menu_btn.setProperty("testid", f"task-card-{task.id}-menu")
        self._content_col.setProperty("testid", f"task-card-{task.id}-content")
        self._status_col.setProperty("testid", f"task-card-{task.id}-status-column")
        self._actions_row.setProperty("testid", f"task-card-{task.id}-actions")
        self._edit_btn.setProperty("testid", f"task-card-{task.id}-edit")
        self._edit_btn.setAccessibleName(f"Editar task {task.id}")
        self._schedule_btn.setProperty("testid", f"task-card-{task.id}-schedule")
        self._schedule_btn.setAccessibleName(f"Agendar task permanente {task.id}")
        self._schedule_btn.setVisible(task.permanente)
        self._delete_btn.setProperty("testid", f"task-card-{task.id}-delete")
        self._delete_btn.setAccessibleName(f"Excluir task {task.id}")
        self._title_edit.setProperty("testid", f"task-card-{task.id}-title-edit")
        self._star_btn.setProperty("testid", f"task-card-{task.id}-favorito")
        self._coin_btn.setProperty("testid", f"task-card-{task.id}-favorito-moeda")
        self._id_label.setText(f"#{task.id}")
        # Re-sincroniza a estrela com a task recarregada sem disparar autosave
        # e cancela qualquer debounce/lockout pendente do estado anterior.
        self._fav_debounce.stop()
        self._coin_debounce.stop()
        self._fav_pending_value = task.favorito
        with QSignalBlocker(self._star_btn):
            self._star_btn.setChecked(task.favorito)
        self._refresh_star_icon()
        self._set_star_pending(False)
        self._set_star_in_flight(False)
        coin_saved = bool(
            self._callbacks.get("is_coin_favorite", lambda _tid: False)(task.id)
        )
        self._coin_pending_value = coin_saved
        with QSignalBlocker(self._coin_btn):
            self._coin_btn.setChecked(coin_saved)
        self._refresh_coin_icon()
        self._set_coin_pending(False)
        self._set_coin_in_flight(False)
        self._refresh_text_content()
        self._seg_ctrl.update_task(task, self._all_tasks)
        self._apply_card_style()
