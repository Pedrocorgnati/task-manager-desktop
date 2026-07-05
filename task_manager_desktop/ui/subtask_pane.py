from __future__ import annotations

import logging
import random
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QDropEvent, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.core.filters import ALL_TASK_TYPES
from task_manager_desktop.core.models import Status, Subtask, Task, TaskType
from task_manager_desktop.core.sector import count_open_deps
from task_manager_desktop.ui.icons import (
    BROOM_SVG,
    CLOCK_SVG,
    svg_to_icon,
    svg_to_pixmap,
    type_icon_svg,
)

if TYPE_CHECKING:
    from task_manager_desktop.repositories.task_repository import TaskRepository

_log = logging.getLogger(__name__)

_ROLE_SUBTASK_ID = Qt.ItemDataRole.UserRole + 1
_ROLE_TEXT = Qt.ItemDataRole.UserRole + 2
_ROLE_PARENT_TASK_ID = Qt.ItemDataRole.UserRole + 3
_EXPANDED_MARGINS = (8, 10, 8, 10)
_COLLAPSED_MARGINS = (2, 10, 2, 10)
_EXPANDED_WIDTH = 260
_SUBTASK_CHECKBOX_WIDTH = 20
# Gap entre o checkbox e o card: metade do valor anterior (7 -> 4, ~7/2 arredondado).
_SUBTASK_ROW_SPACING = 4
_SUBTASK_CARD_WIDTH = int(
    (
        _EXPANDED_WIDTH
        - _EXPANDED_MARGINS[0]
        - _EXPANDED_MARGINS[2]
        - _SUBTASK_CHECKBOX_WIDTH
        - _SUBTASK_ROW_SPACING
    )
    * 0.92
)

# --- medicao de altura da subtask via QLabel.heightForWidth -----------------
# Componentes horizontais internos do card (ver card_layout em _SubtaskRow):
# margens esquerda+direita (4+4), espacamento interno (4) e o slot fixo do
# chevron de notas (retainSizeWhenHidden=True, sempre reservado).
_SUBTASK_CARD_H_PADDING = 8
_SUBTASK_CARD_INNER_SPACING = 4
_SUBTASK_NOTES_TOGGLE_WIDTH = 20
# Chip do icone de tipo (agent/dev/human) no canto superior esquerdo do card.
# Consome largura horizontal do card -> entra no calculo de _SUBTASK_TEXT_WIDTH
# para que heightForWidth meca o wrap do texto com a largura efetiva real.
_SUBTASK_TYPE_ICON_WIDTH = 18
# Largura total (px) do QLabel#subtaskText — passada a heightForWidth para que
# o QSS (padding:4px 4px) seja contabilizado no calculo de wrap interno. O card
# tem agora 3 itens horizontais (icone de tipo, texto, chevron de notas), logo
# dois gaps de _SUBTASK_CARD_INNER_SPACING entre eles.
_SUBTASK_TEXT_WIDTH = (
    _SUBTASK_CARD_WIDTH
    - _SUBTASK_CARD_H_PADDING
    - _SUBTASK_TYPE_ICON_WIDTH
    - _SUBTASK_CARD_INNER_SPACING  # gap icone <-> texto
    - _SUBTASK_CARD_INNER_SPACING  # gap texto <-> chevron de notas
    - _SUBTASK_NOTES_TOGGLE_WIDTH
)
# Cromo vertical (px) somado a altura medida do texto: margens verticais do
# card (4+4), margens externas do row (1+1) e folga visual.
_SUBTASK_ROW_VPADDING = 16
# Altura extra (px) de uma subtask expandida: editor de notas QPlainTextEdit
# fixo em 70 + espacamento do QVBoxLayout do row.
_SUBTASK_EXPANDED_EXTRA = 78
_ALL_SUBTASK_PARENT_TITLE_EXTRA = 24

SUBTASK_FALLBACK_HEIGHT = 24
"""Altura minima (px) do bloco de texto de uma subtask.

Cumpre dois papeis:
- piso da medicao: textos curtos (1 linha) nao colapsam a linha;
- fallback quando ``QApplication.instance() is None`` -- em testes headless,
  sem event loop Qt, ``QLabel.heightForWidth`` nao dispoe de font system. O
  valor 24 e suficiente para esses testes rodarem de forma determinista.
"""

_COLORS = [
    "#F97316",
    "#FBBF24",
    "#22C55E",
    "#06B6D4",
    "#38BDF8",
    "#A78BFA",
    "#FB7185",
]

# Ordem canonica do ciclo de tipo ao clicar no icone do card de subtask. Mesma
# sequencia do radio do modal de criacao (_prompt_new_subtask): agent -> human
# -> dev -> agent. Clicar exatamente sobre o icone avanca para o proximo tipo.
_TYPE_CYCLE = (TaskType.AGENT, TaskType.HUMAN, TaskType.DEV)

_CLOCK_TIMER_DEFAULT_COLOR = "#71717A"
_CLOCK_TIMER_COLORS = [
    ("cinza", "#71717A"),
    ("azul", "#3B82F6"),
    ("marrom", "#92400E"),
    ("verde", "#22C55E"),
    ("amarelo", "#FBBF24"),
    ("vermelho", "#EF4444"),
]
_CLOCK_TIMER_COLOR_VALUES = {color for _, color in _CLOCK_TIMER_COLORS}


def _white_type_icon_svg(task_type: TaskType) -> str:
    svg = type_icon_svg(task_type)
    for color in ("#3B82F6", "#18181B", "#F8FAFC"):
        svg = svg.replace(color, "#FFFFFF")
    return svg


class _SubtaskRow(QWidget):
    def __init__(
        self,
        subtask: Subtask,
        on_notes_changed: Callable[[Subtask, str], None],
        on_expanded_changed: Callable[[bool], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._subtask = subtask
        self._on_notes_changed = on_notes_changed
        self._on_expanded_changed = on_expanded_changed
        self._expanded = False
        self._compact = False
        self._hovered = False
        self.setObjectName("subtaskRow")
        self.setProperty("testid", f"subtask-row-{subtask.id}")
        self.setProperty("state", subtask.state)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

        self.checkbox = QCheckBox(self)
        self.checkbox.setObjectName("subtaskCheckbox")
        self.checkbox.setProperty("testid", f"subtask-checkbox-{subtask.id}")
        self.checkbox.setTristate(True)
        self.checkbox.setCheckState(self._qt_state(subtask.state))
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkbox.setFixedWidth(_SUBTASK_CHECKBOX_WIDTH)

        self._card = QWidget(self)
        self._card.setObjectName("subtaskCard")
        self._card.setProperty("testid", f"subtask-card-{subtask.id}")
        self._card.setProperty("state", subtask.state)
        self._card.setFixedWidth(_SUBTASK_CARD_WIDTH)
        self._card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Icone de tipo (mesmo glifo do card principal) no canto superior
        # esquerdo do card. Recebe um chip translucido escuro para legibilidade
        # uniforme sobre qualquer cor de fundo do card de subtask.
        self.type_icon = QLabel(self._card)
        self.type_icon.setObjectName("subtaskTypeIcon")
        self.type_icon.setProperty("testid", f"subtask-type-icon-{subtask.id}")
        self.type_icon.setFixedSize(_SUBTASK_TYPE_ICON_WIDTH, _SUBTASK_TYPE_ICON_WIDTH)
        self.type_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.type_icon.setToolTip(subtask.type.value)
        self.type_icon.setPixmap(svg_to_pixmap(_white_type_icon_svg(subtask.type), 14))
        self.type_icon.setStyleSheet(
            "QLabel#subtaskTypeIcon { background: rgba(5,6,8,0.50);"
            " border-radius: 5px; }"
        )
        # Clicar exatamente sobre o icone revezar para o proximo tipo (agent ->
        # human -> dev -> agent). Espelha o padrao de mouseDoubleClickEvent do
        # label para a edicao inline: substituicao direta do handler do QLabel.
        self.type_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.type_icon.mousePressEvent = self._on_type_icon_clicked

        self.label = QLabel(subtask.text, self)
        self.label.setObjectName("subtaskText")
        self.label.setProperty("testid", f"subtask-text-{subtask.id}")
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        self.label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.label.setProperty("color", subtask.color)
        self.label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.label.mouseDoubleClickEvent = lambda _event: self._begin_inline_edit()

        self._inline_edit = QLineEdit(self)
        self._inline_edit.setObjectName("subtaskInlineEdit")
        self._inline_edit.setProperty("testid", f"subtask-inline-edit-{subtask.id}")
        self._inline_edit.setText(subtask.text)
        self._inline_edit.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self._inline_edit.hide()
        self._inline_edit.editingFinished.connect(self._commit_inline_edit)
        self._inline_edit.returnPressed.connect(self._commit_inline_edit)

        self.notes_toggle = QToolButton(self)
        self.notes_toggle.setObjectName("subtaskNotesToggle")
        self.notes_toggle.setProperty("testid", f"subtask-notes-toggle-{subtask.id}")
        self.notes_toggle.setAccessibleName("Abrir notas da subtask")
        self.notes_toggle.setFixedSize(20, 20)
        self.notes_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        # Reserva o slot do chevron no layout: mostrar/ocultar no hover apenas
        # alterna a visibilidade, sem refluir o texto (sem efeito de "deslizar").
        _toggle_policy = self.notes_toggle.sizePolicy()
        _toggle_policy.setRetainSizeWhenHidden(True)
        self.notes_toggle.setSizePolicy(_toggle_policy)

        self.notes_editor = QPlainTextEdit(self)
        self.notes_editor.setObjectName("subtaskNotesEditor")
        self.notes_editor.setProperty("testid", f"subtask-notes-editor-{subtask.id}")
        self.notes_editor.setPlaceholderText("Notas da subtask...")
        self.notes_editor.setPlainText(subtask.notes)
        self.notes_editor.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.notes_editor.setFixedHeight(70)
        self.notes_editor.hide()

        card_layout = QHBoxLayout(self._card)
        card_layout.setContentsMargins(4, 4, 4, 4)
        card_layout.setSpacing(_SUBTASK_CARD_INNER_SPACING)
        card_layout.addWidget(self.type_icon, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        card_layout.addWidget(self.label, 1)
        card_layout.addWidget(self._inline_edit, 1)
        card_layout.addWidget(self.notes_toggle, 0, Qt.AlignmentFlag.AlignVCenter)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(_SUBTASK_ROW_SPACING)
        top_row.addWidget(self.checkbox, 0, Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(self._card, 0, Qt.AlignmentFlag.AlignVCenter)
        top_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(5)
        layout.addLayout(top_row)
        layout.addWidget(self.notes_editor)

        self.notes_toggle.clicked.connect(self.toggle_notes)
        self.notes_editor.textChanged.connect(self._autosave_notes)
        self.apply_state(subtask.state)
        self._sync_notes_toggle()

    def set_compact(self, compact: bool) -> None:
        self._compact = compact
        self.checkbox.setVisible(not compact)
        self.label.setVisible(not compact and self._inline_edit.isHidden())
        self._inline_edit.setVisible(False)
        # No modo colapsado o card encolhe para 24px e so o chevron de notas
        # aparece; o chip de tipo nao cabe e e ocultado.
        self.type_icon.setVisible(not compact)
        if compact:
            self._card.setFixedWidth(24)
        else:
            self._card.setFixedWidth(_SUBTASK_CARD_WIDTH)
        self._sync_notes_toggle()

    def apply_state(self, state: int) -> None:
        self._subtask.state = state
        self._subtask.done = state == 2
        self.setProperty("state", state)
        self._card.setProperty("state", state)
        self.style().unpolish(self)
        self.style().polish(self)
        self._card.style().unpolish(self._card)
        self._card.style().polish(self._card)
        font = QFont(self.label.font())
        font.setStrikeOut(state == 2)
        self.label.setFont(font)
        base_color = self._subtask.color
        if state == 1:
            card_bg, text_color = "#22C55E", "#052E16"
        else:
            card_bg, text_color = base_color, "#111116"
        # A parte colorida ocupa o card inteiro (esta div); o chevron de notas,
        # filho do card_layout, passa a ficar dentro dessa area colorida.
        self._card.setStyleSheet(
            f"QWidget#subtaskCard {{ background: {card_bg};"
            " border: none; border-radius: 8px; }"
        )
        self.label.setStyleSheet(f"color: {text_color}; background: transparent;")

    def toggle_notes(self) -> None:
        self._expanded = not self._expanded
        self.notes_editor.setVisible(self._expanded)
        self.notes_toggle.setAccessibleName(
            "Fechar notas da subtask" if self._expanded else "Abrir notas da subtask"
        )
        self._sync_notes_toggle()
        self._on_expanded_changed(self._expanded)
        if self._expanded:
            self.notes_editor.setFocus(Qt.FocusReason.MouseFocusReason)

    def _autosave_notes(self) -> None:
        notes = self.notes_editor.toPlainText()
        if notes == self._subtask.notes:
            return
        self._subtask.notes = notes
        self._on_notes_changed(self._subtask, notes)
        self._sync_notes_toggle()

    def _has_notes(self) -> bool:
        return bool(self._subtask.notes.strip())

    def _sync_notes_toggle(self) -> None:
        has_notes = self._has_notes()
        if self._compact:
            self.notes_toggle.setVisible(True)
        else:
            self.notes_toggle.setVisible(self._expanded or self._hovered or has_notes)
        self.notes_toggle.setText("⌃" if self._expanded else "⌄")
        self.notes_toggle.setProperty("hasNotes", has_notes)
        if has_notes:
            self.notes_toggle.setStyleSheet(
                "QToolButton#subtaskNotesToggle {"
                "background: rgba(5,6,8,0.25); color: #111116;"
                "border: none; border-radius: 6px; font-size: 15px; font-weight: 900; padding: 0;"
                "}"
            )
        else:
            self.notes_toggle.setStyleSheet(
                "QToolButton#subtaskNotesToggle {"
                "background: transparent; color: #111116;"
                "border: none; border-radius: 6px; font-size: 13px; font-weight: 700; padding: 0;"
                "}"
                "QToolButton#subtaskNotesToggle:hover {"
                "color: #111116;"
                "}"
            )

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._hovered = True
        self._sync_notes_toggle()
        if event is not None:
            super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._hovered = False
        self._sync_notes_toggle()
        if event is not None:
            super().leaveEvent(event)

    @staticmethod
    def _qt_state(state: int) -> Qt.CheckState:
        if state == 1:
            return Qt.CheckState.PartiallyChecked
        if state == 2:
            return Qt.CheckState.Checked
        return Qt.CheckState.Unchecked

    @property
    def is_expanded(self) -> bool:
        """Indica se o editor de notas esta visivel (afeta a altura do row)."""
        return self._expanded

    def _begin_inline_edit(self) -> None:
        if self._compact:
            return
        self._inline_edit.setText(self._subtask.text)
        self.label.hide()
        self._inline_edit.show()
        self._inline_edit.setFocus(Qt.FocusReason.MouseFocusReason)
        self._inline_edit.selectAll()

    def _resolve_pane(self) -> SubtaskPane | None:
        parent = self.parent()
        while parent is not None:
            pane = getattr(parent, "_pane", None)
            if isinstance(pane, SubtaskPane):
                return pane
            if isinstance(parent, SubtaskPane):
                return parent
            parent = parent.parent()
        return None

    def _commit_inline_edit(self) -> None:
        if self._inline_edit.isHidden():
            return
        new_text = self._inline_edit.text().strip()
        old_text = self._subtask.text
        if new_text and new_text != old_text:
            # Aplica otimisticamente; a pane persiste e, em caso de falha de
            # I/O, chama revert_inline_edit() para desfazer model + label.
            self._subtask.text = new_text
            self.label.setText(new_text)
        self._inline_edit.hide()
        self.label.show()
        pane = self._resolve_pane()
        if pane is not None and new_text and new_text != old_text:
            pane._commit_subtask_text(self._subtask, self, old_text)

    def revert_inline_edit(self, old_text: str) -> None:
        """Desfaz visualmente a edicao inline apos falha de persistencia.

        Espelha o padrao de rollback do autosave da estrela favorito: o texto
        do modelo e do label voltam ao valor anterior e a borda do card ganha
        uma indicacao de erro discreta (sem dialog modal — erro desfazivel)."""
        self._subtask.text = old_text
        self.label.setText(old_text)
        self._inline_edit.setText(old_text)
        self._flash_edit_error()

    def _flash_edit_error(self) -> None:
        """Indicacao de erro discreta: borda vermelha temporaria no card."""
        self._card.setStyleSheet(
            self._card.styleSheet()
            + " QWidget#subtaskCard { border: 1px solid #EF4444; }"
        )
        self.setToolTip("Falha ao salvar a subtask. Texto revertido.")
        QTimer.singleShot(2000, self._clear_edit_error)

    def _clear_edit_error(self) -> None:
        # Reaplica o estilo canonico do estado atual (limpa a borda de erro).
        self.apply_state(self._subtask.state)
        self.setToolTip("")

    def _on_type_icon_clicked(self, event) -> None:
        """Revezar o tipo da subtask ao clicar exatamente sobre o icone.

        Apenas o botao esquerdo cicla; no modo colapsado o icone esta oculto e o
        clique e ignorado. A persistencia (com rollback em falha de I/O) e
        delegada a pane via `_commit_subtask_type`.
        """
        if event is not None and event.button() != Qt.MouseButton.LeftButton:
            return
        if self._compact:
            return
        self._cycle_type()

    def _cycle_type(self) -> None:
        old_type = self._subtask.type
        idx = _TYPE_CYCLE.index(old_type) if old_type in _TYPE_CYCLE else 0
        new_type = _TYPE_CYCLE[(idx + 1) % len(_TYPE_CYCLE)]
        self._apply_type(new_type)
        pane = self._resolve_pane()
        if pane is not None:
            pane._commit_subtask_type(self._subtask, self, old_type)

    def _apply_type(self, task_type: TaskType) -> None:
        """Atualiza modelo + glifo + tooltip do icone de tipo (sem persistir)."""
        self._subtask.type = task_type
        self.type_icon.setToolTip(task_type.value)
        self.type_icon.setPixmap(svg_to_pixmap(_white_type_icon_svg(task_type), 14))

    def revert_type(self, old_type: TaskType) -> None:
        """Desfaz visualmente o ciclo de tipo apos falha de persistencia.

        Espelha `revert_inline_edit`: modelo + icone voltam ao tipo anterior e o
        card pisca a borda de erro (sem dialog modal — erro desfazivel)."""
        self._apply_type(old_type)
        self._flash_edit_error()


class _AllSubtaskRow(_SubtaskRow):
    def __init__(
        self,
        subtask: Subtask,
        parent_task: Task,
        on_notes_changed: Callable[[Subtask, str], None],
        on_expanded_changed: Callable[[bool], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(subtask, on_notes_changed, on_expanded_changed, parent)
        self._parent_task = parent_task
        self.setObjectName("allSubtaskRow")
        self.setProperty("testid", f"all-subtask-row-{subtask.id}")
        self._card.setProperty("testid", f"all-subtask-card-{subtask.id}")

        self.parent_title = QLabel(parent_task.title, self)
        self.parent_title.setObjectName("allSubtaskParentTitle")
        self.parent_title.setProperty("testid", f"all-subtask-parent-title-{subtask.id}")
        self.parent_title.setTextFormat(Qt.TextFormat.PlainText)
        self.parent_title.setWordWrap(True)
        self.parent_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.parent_title.setFixedWidth(_SUBTASK_CARD_WIDTH)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(_SUBTASK_ROW_SPACING)
        title_row.addSpacing(_SUBTASK_CHECKBOX_WIDTH)
        title_row.addWidget(self.parent_title, 0, Qt.AlignmentFlag.AlignVCenter)
        title_row.addStretch(1)

        layout = self.layout()
        if isinstance(layout, QVBoxLayout):
            layout.insertLayout(0, title_row)

    def set_compact(self, compact: bool) -> None:
        super().set_compact(compact)
        self.parent_title.setVisible(not compact)


class _SubtaskList(QListWidget):
    def __init__(self, pane: SubtaskPane) -> None:
        super().__init__(pane)
        self._pane = pane
        self.setObjectName("subtaskList")
        self.setProperty("testid", "subtask-list")
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Rolagem suave por pixel (espelha a lista principal): sem ScrollPerItem
        # a coluna de subtasks desce fracao de card por entalhe, em vez de pular
        # um card inteiro.
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(18)
        # Gap entre cards: metade do valor anterior (2 -> 1).
        self.setSpacing(1)
        self._animations: list[QPropertyAnimation] = []

    def dropEvent(self, event: QDropEvent) -> None:
        before = self._capture_item_positions()
        source_row = self.currentRow()
        pos = event.position().toPoint()
        target_item = self.itemAt(pos)
        target_row = self.row(target_item) if target_item is not None else -1

        if (
            event.source() is self
            and source_row >= 0
            and target_row >= 0
            and source_row != target_row
            and self.dropIndicatorPosition() == QAbstractItemView.DropIndicatorPosition.OnItem
        ):
            item = self.takeItem(source_row)
            if source_row < target_row:
                target_row -= 1
            self.insertItem(target_row, item)
            self.setCurrentRow(target_row)
            event.accept()
        else:
            super().dropEvent(event)

        self._animate_reorder(before)
        self._pane.persist_order()

    def _capture_item_positions(self) -> dict[str, QPoint]:
        positions: dict[str, QPoint] = {}
        for row in range(self.count()):
            item = self.item(row)
            widget = self.itemWidget(item)
            subtask_id = str(item.data(_ROLE_SUBTASK_ID))
            if widget is not None:
                positions[subtask_id] = widget.pos()
        return positions

    def _animate_reorder(self, before: dict[str, QPoint]) -> None:
        self._animations.clear()
        for row in range(self.count()):
            item = self.item(row)
            widget = self.itemWidget(item)
            if widget is None:
                continue
            subtask_id = str(item.data(_ROLE_SUBTASK_ID))
            old_pos = before.get(subtask_id)
            if old_pos is None:
                continue
            new_pos = widget.pos()
            if old_pos == new_pos:
                continue
            widget.move(old_pos)
            anim = QPropertyAnimation(widget, b"pos", self)
            anim.setDuration(140)
            anim.setStartValue(old_pos)
            anim.setEndValue(new_pos)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()
            self._animations.append(anim)


class SubtaskPane(QWidget):
    """Painel central de subtasks vinculadas ao id da task selecionada."""

    def __init__(self, repo: TaskRepository | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._task: Task | None = None
        self._collapsed = False
        self._show_all = False
        self._show_all_task_ids: set[str] = set()
        # Filtro de tipo herdado do header (data-testid="header-type-filter").
        # Vale tanto no modo normal quanto no Show All. Default: todos os tipos.
        self._task_types: frozenset[str] = ALL_TASK_TYPES
        # Callback opcional disparado quando a composicao de subtasks muda
        # (criar/limpar). A lista de cards principais reavalia o filtro de tipo:
        # criar uma subtask agent pode fazer o card aparecer sob "so agent", e
        # limpar a ultima subtask de um tipo pode faze-lo sumir.
        self._on_subtasks_changed: Callable[[], None] | None = None
        self.setObjectName("subtaskPane")
        self.setAccessibleName("Painel de subtasks")
        self.setProperty("testid", "subtask-pane")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(_EXPANDED_WIDTH)

        self.btn_toggle = QPushButton("[<]", self)
        self.btn_toggle.setObjectName("middleColumnToggle")
        self.btn_toggle.setAccessibleName("Colapsar painel de subtasks")
        self.btn_toggle.setProperty("testid", "subtask-toggle-button")
        self.btn_toggle.setFixedHeight(30)

        self.btn_add = QPushButton("+", self)
        self.btn_add.setObjectName("subtaskAddButton")
        self.btn_add.setProperty("testid", "subtask-add-button")
        self.btn_add.setAccessibleName("Adicionar subtask")
        self.btn_add.setFixedSize(30, 30)
        self.btn_add.setEnabled(False)

        self.btn_show_all = QPushButton("Show All", self)
        self.btn_show_all.setObjectName("subtaskShowAllButton")
        self.btn_show_all.setProperty("testid", "subtask-show-all-button")
        self.btn_show_all.setAccessibleName("Mostrar subtasks de todas as tasks em progresso")
        self.btn_show_all.setCheckable(True)
        self.btn_show_all.setFixedHeight(30)
        self.btn_show_all.setEnabled(repo is not None)
        self.btn_show_all.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_clear_done = QToolButton(self)
        self.btn_clear_done.setObjectName("subtaskClearDoneButton")
        self.btn_clear_done.setProperty("testid", "subtask-clear-done-button")
        self.btn_clear_done.setAccessibleName("Limpar subtasks concluídas")
        self.btn_clear_done.setToolTip("Nenhuma subtask concluída neste grupo")
        self.btn_clear_done.setIcon(svg_to_icon(BROOM_SVG, 16))
        self.btn_clear_done.setIconSize(QSize(16, 16))
        self.btn_clear_done.setFixedSize(30, 30)
        self.btn_clear_done.setEnabled(False)
        self.btn_clear_done.setCursor(Qt.CursorShape.PointingHandCursor)

        self._body_title = QLabel("Subtasks", self)
        self._body_title.setObjectName("subtaskPaneBodyTitle")
        self._body_title.setProperty("testid", "subtask-pane-title")
        self._body_title.setTextFormat(Qt.TextFormat.PlainText)
        self._body_title.setWordWrap(True)
        self._body_title.setFixedHeight(18)

        self._header = QWidget(self)
        self._header.setObjectName("subtaskPaneHeader")
        self._header.setProperty("testid", "subtasks-header")
        self._header.setFixedHeight(30)
        self._header_layout = QHBoxLayout(self._header)
        self._header_layout.setContentsMargins(0, 0, 0, 0)
        self._header_layout.setSpacing(6)
        self._header_layout.addWidget(self.btn_toggle)
        self._header_layout.addStretch(1)
        self._header_layout.addWidget(self.btn_show_all)
        self._header_layout.addWidget(self.btn_add)
        self._header_layout.addWidget(self.btn_clear_done)
        self._main_header_layout = self._header_layout
        self._subheader_buttons = self._header_layout

        self._empty = QLabel("Selecione uma task", self)
        self._empty.setObjectName("subtaskEmpty")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setWordWrap(True)

        self._list = _SubtaskList(self)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(*_EXPANDED_MARGINS)
        self._layout.setSpacing(8)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layout.addWidget(self._header)
        self._layout.addWidget(self._body_title)
        self._layout.addWidget(self._empty)
        self._layout.addWidget(self._list, 1)

        self.btn_add.clicked.connect(self._add_subtask)
        self.btn_show_all.toggled.connect(self._set_show_all)
        self.btn_clear_done.clicked.connect(self._clear_done_subtasks)
        self.set_task(None)

    def collapsed_width(self) -> int:
        """Width for collapsed splitter state: toggle button + 2px each side."""
        return self.btn_toggle.sizeHint().width() + _COLLAPSED_MARGINS[0] + _COLLAPSED_MARGINS[2]

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self.btn_toggle.setText("[>]" if collapsed else "[<]")
        self.btn_toggle.setAccessibleName(
            "Expandir painel de subtasks" if collapsed else "Colapsar painel de subtasks"
        )
        self._layout.setContentsMargins(*(_COLLAPSED_MARGINS if collapsed else _EXPANDED_MARGINS))
        self._header_layout.setSpacing(6)
        self.btn_add.setVisible(not collapsed)
        self.btn_show_all.setVisible(not collapsed)
        self.btn_clear_done.setVisible(not collapsed)
        has_context = self._show_all or self._task is not None
        self._body_title.setVisible(not collapsed)
        self._list.setVisible(not collapsed and has_context and self._list.count() > 0)
        self._empty.setVisible(not collapsed and (not has_context or self._list.count() == 0))
        for row_idx in range(self._list.count()):
            item = self._list.item(row_idx)
            widget = self._list.itemWidget(item)
            if isinstance(widget, _SubtaskRow):
                widget.set_compact(collapsed)
        collapsed_width = self.collapsed_width()
        target_width = collapsed_width if collapsed else _EXPANDED_WIDTH
        self.setMinimumWidth(target_width)
        self.setMaximumWidth(target_width)
        self.updateGeometry()

    def set_task(self, task: Task | None) -> None:
        self._task = task
        self.btn_add.setEnabled(task is not None and not self._show_all)
        self.btn_clear_done.setEnabled(False)
        self._sync_body_title()
        self._body_title.setVisible(not self._collapsed)
        self.refresh()

    def set_type_filter(self, task_types: object) -> None:
        """Aplica o filtro de tipo do header (header-type-filter) as subtasks.

        Aceita um iteravel de TaskType/str (ou None para "todos"). Idempotente:
        so refaz a lista quando o conjunto de tipos muda. Vale tanto no modo
        normal quanto no Show All.
        """
        if task_types is None:
            normalized = ALL_TASK_TYPES
        else:
            normalized = frozenset(
                t.value if isinstance(t, TaskType) else str(t) for t in task_types
            )
        if normalized == self._task_types:
            return
        self._task_types = normalized
        self.refresh()

    def set_on_subtasks_changed(self, callback: Callable[[], None] | None) -> None:
        """Registra o callback de mudanca de composicao de subtasks (criar/limpar)."""
        self._on_subtasks_changed = callback

    def _notify_subtasks_changed(self) -> None:
        if self._on_subtasks_changed is not None:
            self._on_subtasks_changed()

    def refresh(self) -> None:
        self._list.clear()
        self._show_all_task_ids.clear()
        # Reordenar por DnD so faz sentido sobre a lista completa: sob filtro de
        # tipo ativo a view e parcial e persistir a ordem renumeraria apenas os
        # visiveis, embaralhando os ocultos. Desabilita o DnD nesse caso.
        self._list.setDragDropMode(
            QAbstractItemView.DragDropMode.NoDragDrop
            if self._show_all or self._task_types != ALL_TASK_TYPES
            else QAbstractItemView.DragDropMode.InternalMove
        )
        if self._show_all:
            self._refresh_all_in_progress_subtasks()
            return
        if self._task is None or self._repo is None:
            self._empty.setText("Selecione uma task")
            self._empty.show()
            self._list.hide()
            self._set_clear_done_enabled(False)
            return
        all_subtasks = self._repo.list_subtasks(self._task.id)
        subtasks = [s for s in all_subtasks if s.type.value in self._task_types]
        if not subtasks:
            # Distingue "task sem subtasks" (vazio mudo) de "todas filtradas
            # pelo tipo" (Zero Silencio: sinaliza por que a lista esta vazia).
            self._empty.setText(
                "Nenhuma subtask do tipo filtrado" if all_subtasks else ""
            )
            self._empty.show()
            self._list.hide()
            self._set_clear_done_enabled(False)
            return
        self._empty.hide()
        self._list.show()
        for subtask in subtasks:
            self._add_item(subtask)
        self._set_clear_done_enabled(any(subtask.state == 2 for subtask in subtasks))

    def persist_order(self) -> None:
        if self._repo is None or self._show_all:
            return
        pairs = []
        for row in range(self._list.count()):
            item = self._list.item(row)
            pairs.append((str(item.data(_ROLE_SUBTASK_ID)), row + 1))
        self._repo.update_subtask_order_indexes(pairs)

    def _add_item(self, subtask: Subtask) -> None:
        item = QListWidgetItem()
        item.setData(_ROLE_SUBTASK_ID, subtask.id)
        item.setData(_ROLE_TEXT, subtask.text)
        item.setFlags(
            Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsDragEnabled
        )
        item.setSizeHint(QSize(1, self._row_height(subtask.text, expanded=False)))
        self._list.addItem(item)

        row = _SubtaskRow(
            subtask,
            self._save_subtask_notes,
            lambda expanded, i=item, s=subtask: self._resize_subtask_item(i, s, expanded),
            self._list,
        )
        row.checkbox.stateChanged.connect(lambda state, s=subtask, r=row: self._set_state(s, r, state))
        row.set_compact(self._collapsed)
        self._list.setItemWidget(item, row)

    def _add_all_item(self, subtask: Subtask, parent_task: Task) -> None:
        item = QListWidgetItem()
        item.setData(_ROLE_SUBTASK_ID, subtask.id)
        item.setData(_ROLE_TEXT, subtask.text)
        item.setData(_ROLE_PARENT_TASK_ID, parent_task.id)
        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        item.setSizeHint(QSize(1, self._row_height(subtask.text, expanded=False, show_parent=True)))
        self._list.addItem(item)

        row = _AllSubtaskRow(
            subtask,
            parent_task,
            self._save_subtask_notes,
            lambda expanded, i=item, s=subtask: self._resize_subtask_item(
                i, s, expanded, show_parent=True
            ),
            self._list,
        )
        row.checkbox.stateChanged.connect(lambda state, s=subtask, r=row: self._set_state(s, r, state))
        row.set_compact(self._collapsed)
        self._list.setItemWidget(item, row)

    def _refresh_all_in_progress_subtasks(self) -> None:
        if self._repo is None:
            self._empty.setText("Sem repositório")
            self._empty.show()
            self._list.hide()
            self._set_clear_done_enabled(False)
            return

        all_pairs: list[tuple[Task, Subtask]] = []
        for task in self._green_in_progress_tasks():
            all_pairs.extend((task, subtask) for subtask in self._repo.list_subtasks(task.id))

        # Show All tambem respeita o filtro de tipo do header.
        pairs = [(t, s) for (t, s) in all_pairs if s.type.value in self._task_types]

        if not pairs:
            self._empty.setText(
                "Nenhuma subtask do tipo filtrado"
                if all_pairs
                else "Nenhuma subtask em tasks In Progress verdes"
            )
            self._empty.show()
            self._list.hide()
            self._set_clear_done_enabled(False)
            return

        self._empty.hide()
        self._list.show()
        for task, subtask in pairs:
            self._add_all_item(subtask, task)
        self._show_all_task_ids = {task.id for task, _subtask in pairs}
        self._set_clear_done_enabled(any(subtask.state == 2 for _task, subtask in pairs))

    def _green_in_progress_tasks(self) -> list[Task]:
        if self._repo is None:
            return []
        tasks = self._repo.list_active()
        all_tasks = {task.id: task for task in tasks}
        return [
            task
            for task in tasks
            if task.status == Status.IN_PROGRESS and count_open_deps(task.deps, all_tasks) == 0
        ]

    def _measure_subtask_text_height(self, text: str) -> int:
        """Altura (px) do texto da subtask com wrap na largura efetiva do card.

        Usa QLabel.heightForWidth com objectName "subtaskText" para que o QSS
        do tema (font-size:10px; font-weight:600; padding:4px 4px) seja
        aplicado via ensurePolished. A abordagem anterior com QFontMetrics
        usava self.font() (13px 400) e ignorava tanto o peso de fonte quanto o
        padding horizontal do label real, subestimando a altura em casos de
        texto borderline de 3 linhas.
        Sem QApplication ativa (testes headless): retorna SUBTASK_FALLBACK_HEIGHT.
        """
        if QApplication.instance() is None:
            return SUBTASK_FALLBACK_HEIGHT
        tmp = QLabel(text)
        tmp.setObjectName("subtaskText")
        tmp.setWordWrap(True)
        tmp.setTextFormat(Qt.TextFormat.PlainText)
        tmp.ensurePolished()
        h = tmp.heightForWidth(_SUBTASK_TEXT_WIDTH)
        return max(h if h > 0 else SUBTASK_FALLBACK_HEIGHT, SUBTASK_FALLBACK_HEIGHT)

    def _row_height(self, text: str, expanded: bool = False, show_parent: bool = False) -> int:
        height = self._measure_subtask_text_height(text) + _SUBTASK_ROW_VPADDING
        if show_parent:
            height += _ALL_SUBTASK_PARENT_TITLE_EXTRA
        if expanded:
            height += _SUBTASK_EXPANDED_EXTRA
        return height

    def _resize_subtask_item(
        self,
        item: QListWidgetItem,
        subtask: Subtask,
        expanded: bool,
        show_parent: bool = False,
    ) -> None:
        item.setSizeHint(
            QSize(1, self._row_height(subtask.text, expanded=expanded, show_parent=show_parent))
        )

    def _save_subtask_notes(self, subtask: Subtask, notes: str) -> None:
        if self._repo is not None:
            self._repo.update_subtask_notes(subtask.id, notes)

    def _find_item(self, subtask_id: str) -> QListWidgetItem | None:
        for row_idx in range(self._list.count()):
            item = self._list.item(row_idx)
            if str(item.data(_ROLE_SUBTASK_ID)) == str(subtask_id):
                return item
        return None

    def _commit_subtask_text(
        self, subtask: Subtask, row: _SubtaskRow, old_text: str
    ) -> None:
        """Persiste a edicao inline de texto e recalcula o sizeHint (AC-5).

        Persiste ANTES de refluir o layout: se a persistencia falha, o texto e
        revertido (model + label) via ``row.revert_inline_edit`` e o sizeHint e
        recalculado com o texto antigo, evitando data loss silenciosa.
        """
        if not self._save_subtask_text(subtask, row, old_text):
            # Falha de I/O: o texto ja foi revertido por revert_inline_edit.
            # Recalcula o sizeHint com o texto restaurado.
            item = self._find_item(subtask.id)
            if item is not None:
                item.setData(_ROLE_TEXT, subtask.text)
                show_parent = isinstance(row, _AllSubtaskRow)
                item.setSizeHint(
                    QSize(
                        1,
                        self._row_height(
                            subtask.text,
                            expanded=row.is_expanded,
                            show_parent=show_parent,
                        ),
                    )
                )
            row.updateGeometry()
            return
        item = self._find_item(subtask.id)
        if item is not None:
            item.setData(_ROLE_TEXT, subtask.text)
            show_parent = isinstance(row, _AllSubtaskRow)
            item.setSizeHint(
                QSize(
                    1,
                    self._row_height(
                        subtask.text,
                        expanded=row.is_expanded,
                        show_parent=show_parent,
                    ),
                )
            )
        row.updateGeometry()

    def _save_subtask_text(
        self, subtask: Subtask, row: _SubtaskRow, old_text: str
    ) -> bool:
        """Persiste o texto da subtask via metodo do repositorio.

        Substitui o antigo RAW ``repo._conn.execute`` sem tratamento de erro
        (data loss silenciosa). Em qualquer falha — I/O, subtask/task ausente,
        violacao de unicidade — reverte a edicao inline visualmente e loga o
        erro com o id da subtask. Retorna True se persistiu, False caso falhe.
        """
        if self._repo is None:
            return False
        try:
            self._repo.update_subtask_text(subtask.id, subtask.text)
        except Exception as exc:  # noqa: BLE001 - rollback uniforme p/ qualquer falha
            _log.error(
                "subtask.inline_edit_persist_failed: %s (subtask_id=%s)",
                exc,
                subtask.id,
            )
            row.revert_inline_edit(old_text)
            return False
        return True

    def _commit_subtask_type(
        self, subtask: Subtask, row: _SubtaskRow, old_type: TaskType
    ) -> None:
        """Persiste o tipo revezado pelo icone do card (com rollback em falha).

        Em sucesso, se ha filtro de tipo ativo e a subtask deixou de casa-lo
        (ex.: virou `dev` sob filtro `agent`), a view e reconstruida para nao
        exibir um card fora do filtro; o `_notify_subtasks_changed` reavalia a
        composicao do filtro de cards principais. O refresh e adiado via
        QTimer para nao destruir o widget do row dentro do seu proprio
        mousePressEvent.
        """
        if self._repo is None:
            return
        try:
            self._repo.update_subtask_type(subtask.id, subtask.type)
        except Exception as exc:  # noqa: BLE001 - rollback uniforme p/ qualquer falha
            _log.error(
                "subtask.type_cycle_persist_failed: %s (subtask_id=%s)",
                exc,
                subtask.id,
            )
            row.revert_type(old_type)
            return
        hidden_by_filter = (
            self._task_types != ALL_TASK_TYPES
            and subtask.type.value not in self._task_types
        )
        if hidden_by_filter:
            QTimer.singleShot(0, self.refresh)
        QTimer.singleShot(0, self._notify_subtasks_changed)

    def _set_state(self, subtask: Subtask, row: _SubtaskRow, qt_state: int) -> None:
        # QCheckBox tri-state usa 0/1/2, exatamente o ciclo pedido.
        state = int(qt_state)
        row.apply_state(state)
        if self._repo is not None:
            self._repo.update_subtask_state(subtask.id, state)
        self._set_clear_done_enabled(self._has_done_subtasks_in_view())

    def _set_show_all(self, enabled: bool) -> None:
        self._show_all = enabled
        self.btn_add.setEnabled(self._task is not None and not enabled)
        self._set_clear_done_enabled(self._has_done_subtasks_in_view())
        self._sync_body_title()
        self.refresh()

    def _sync_body_title(self) -> None:
        if self._show_all:
            self._body_title.setText("Subtasks: In Progress")
        else:
            self._body_title.setText("Subtasks" if self._task is None else f"Subtasks {self._task.title}")

    def _add_subtask(self) -> None:
        if self._task is None or self._repo is None:
            return
        result = self._prompt_new_subtask()
        if result is None:
            return
        text, subtask_type = result
        text = text.strip()
        if not text:
            return
        # Calcula a ordem a partir de TODAS as subtasks (nao so as visiveis sob
        # filtro): self._list.count() conta apenas as visiveis e colidiria com o
        # order_index de subtasks ocultas pelo filtro de tipo.
        existing = self._repo.list_subtasks(self._task.id)
        next_order = max((s.order_index for s in existing), default=0) + 1
        subtask = Subtask(
            id=f"st-{uuid.uuid4().hex[:10]}",
            task_id=self._task.id,
            text=text,
            color=random.choice(_COLORS),
            order_index=next_order,
            type=subtask_type,
        )
        self._repo.create_subtask(subtask)
        self.refresh()
        self._notify_subtasks_changed()

    def _prompt_new_subtask(
        self,
        initial_text: str = "",
        initial_type: TaskType = TaskType.AGENT,
    ) -> tuple[str, TaskType] | None:
        """Modal de criacao de subtask: texto + radio de tipo (agent/human/dev).

        O radio vem com `agent` selecionado por default (mesmo enum do card
        principal). Retorna (texto, tipo) no accept ou None no cancel. Fatorado
        para fora de _add_subtask para ser testavel sem driblar o event loop Qt
        (testes monkeypatcham este metodo).
        """
        from PySide6.QtWidgets import QButtonGroup, QDialog, QRadioButton

        dlg = QDialog(self)
        dlg.setObjectName("subtaskCreateDialog")
        dlg.setProperty("testid", "subtask-modal")
        dlg.setWindowTitle("Nova subtask")
        dlg.setModal(True)
        dlg.setMinimumWidth(320)
        dlg.setStyleSheet(
            "QDialog { background: #111116; }"
            "QLabel#dlgHead { font-size: 15px; font-weight: 700; color: #F8FAFC; }"
            "QLabel#dlgSec  { font-size: 10px; font-weight: 700; color: #71717A;"
            "                  letter-spacing: 1px; }"
            "QLineEdit {"
            "  background: #1C1D24; border: 1px solid #3B3D46; border-radius: 8px;"
            "  padding: 8px 10px; color: #F8FAFC; font-size: 13px; }"
            "QLineEdit:focus { border-color: #FBBF24; }"
            "QRadioButton { color: #E4E4E7; font-size: 13px; font-weight: 600;"
            "               spacing: 6px; }"
            "QRadioButton::indicator { width: 14px; height: 14px; }"
            "QPushButton#okBtn {"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #B45309,stop:1 #FBBF24);"
            "  border: none; border-radius: 8px; color: #0D0E12;"
            "  font-size: 13px; font-weight: 700; padding: 8px 22px; }"
            "QPushButton#okBtn:disabled { background: #27272A; color: #52525B; }"
            "QPushButton#okBtn:hover:!disabled {"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #FBBF24,stop:1 #FDE68A); }"
            "QPushButton#cancelBtn {"
            "  background: transparent; border: 1px solid #3B3D46; border-radius: 8px;"
            "  color: #71717A; font-size: 13px; font-weight: 600; padding: 8px 16px; }"
            "QPushButton#cancelBtn:hover { border-color: #71717A; color: #F8FAFC; }"
        )

        root = QVBoxLayout(dlg)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(0)

        head = QLabel("Nova subtask", dlg)
        head.setObjectName("dlgHead")
        root.addWidget(head)
        root.addSpacing(16)

        lbl_text = QLabel("TEXTO", dlg)
        lbl_text.setObjectName("dlgSec")
        root.addWidget(lbl_text)
        root.addSpacing(4)
        text_input = QLineEdit(dlg)
        text_input.setObjectName("subtaskModalTextInput")
        text_input.setProperty("testid", "subtask-modal-text-input")
        text_input.setPlaceholderText("Texto da subtask")
        text_input.setText(initial_text)
        root.addWidget(text_input)
        root.addSpacing(14)

        lbl_type = QLabel("TIPO", dlg)
        lbl_type.setObjectName("dlgSec")
        root.addWidget(lbl_type)
        root.addSpacing(4)
        type_row = QHBoxLayout()
        type_row.setContentsMargins(0, 0, 0, 0)
        type_row.setSpacing(16)
        type_group = QButtonGroup(dlg)
        type_group.setExclusive(True)
        radios: dict[TaskType, QRadioButton] = {}
        for task_type in (TaskType.AGENT, TaskType.HUMAN, TaskType.DEV):
            radio = QRadioButton(task_type.value.title(), dlg)
            radio.setObjectName(f"subtaskModalType{task_type.value.title()}")
            radio.setProperty("testid", f"subtask-modal-type-{task_type.value}")
            radio.setAccessibleName(f"Tipo {task_type.value}")
            radio.setCursor(Qt.CursorShape.PointingHandCursor)
            type_group.addButton(radio)
            type_row.addWidget(radio)
            radios[task_type] = radio
        type_row.addStretch(1)
        radios.get(initial_type, radios[TaskType.AGENT]).setChecked(True)
        root.addLayout(type_row)
        root.addSpacing(18)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch(1)
        cancel_btn = QPushButton("Cancelar", dlg)
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.setProperty("testid", "subtask-modal-cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn = QPushButton("Adicionar", dlg)
        ok_btn.setObjectName("okBtn")
        ok_btn.setProperty("testid", "subtask-modal-ok")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setDefault(True)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        def _validate() -> None:
            ok_btn.setEnabled(bool(text_input.text().strip()))

        cancel_btn.clicked.connect(dlg.reject)
        ok_btn.clicked.connect(dlg.accept)
        text_input.textChanged.connect(lambda _t: _validate())
        text_input.returnPressed.connect(
            lambda: dlg.accept() if text_input.text().strip() else None
        )
        _validate()
        text_input.setFocus(Qt.FocusReason.OtherFocusReason)

        if dlg.exec() != int(QDialog.DialogCode.Accepted):
            return None
        text = text_input.text().strip()
        if not text:
            return None
        chosen = next(
            (tt for tt, radio in radios.items() if radio.isChecked()),
            TaskType.AGENT,
        )
        return text, chosen

    def _clear_done_subtasks(self) -> None:
        if self._repo is None:
            return
        # Sob filtro de tipo ativo, so apaga as concluidas dos tipos VISIVEIS —
        # nunca subtasks de tipos ocultos pela view (anti perda de dados muda).
        types = None if self._task_types == ALL_TASK_TYPES else set(self._task_types)
        if self._show_all:
            for task_id in sorted(self._show_all_task_ids):
                self._repo.delete_done_subtasks(task_id, types)
            self.refresh()
            self._notify_subtasks_changed()
            return
        if self._task is None:
            return
        self._repo.delete_done_subtasks(self._task.id, types)
        self.refresh()
        self._notify_subtasks_changed()

    def _has_done_subtasks_in_view(self) -> bool:
        for row_idx in range(self._list.count()):
            item = self._list.item(row_idx)
            widget = self._list.itemWidget(item)
            if isinstance(widget, _SubtaskRow) and widget._subtask.state == 2:
                return True
        return False

    def _set_clear_done_enabled(self, enabled: bool) -> None:
        self.btn_clear_done.setEnabled(enabled)
        if enabled:
            if self._show_all:
                self.btn_clear_done.setToolTip("Limpar subtasks concluídas visíveis")
            else:
                self.btn_clear_done.setToolTip("Limpar subtasks concluídas deste grupo")
        else:
            if self._show_all:
                self.btn_clear_done.setToolTip("Nenhuma subtask concluída visível")
            else:
                self.btn_clear_done.setToolTip("Nenhuma subtask concluída neste grupo")


class ClockPane(SubtaskPane):
    """Painel de timers regressivos com persistencia."""

    def __init__(
        self,
        repo: TaskRepository | None = None,
        parent: QWidget | None = None,
        *,
        kind: str = "normal",
        title: str = "Timers",
        pane_testid: str = "clock-pane",
        testid_prefix: str = "clock",
        accessible_name: str = "Painel de clock",
        running_border: str = "#FBBF24",
        running_hover_border: str = "#FDE68A",
    ) -> None:
        # kind/prefixos/cores precisam existir ANTES do super().__init__, pois
        # este dispara refresh()/_add_timer_row() que os consomem.
        self._kind = kind
        self._testid_prefix = testid_prefix
        self._running_border = running_border
        self._running_hover_border = running_hover_border
        super().__init__(repo=repo, parent=parent)
        self.setObjectName("clockPane")
        self.setAccessibleName(accessible_name)
        self.setProperty("testid", pane_testid)
        self.btn_toggle.setAccessibleName("Colapsar painel de clock")
        self.btn_toggle.setProperty("testid", f"{testid_prefix}-toggle-button")
        self.btn_add.setObjectName("clockAddButton")
        self.btn_add.setProperty("testid", f"{testid_prefix}-add-button")
        self.btn_add.setAccessibleName("Adicionar temporizador")
        self.btn_add.setEnabled(True)
        self.btn_show_all.hide()
        self.btn_clear_done.hide()
        self._body_title.setText(title)
        self._body_title.setProperty("testid", f"{testid_prefix}-pane-title")
        self._body_title.show()
        self._empty.setText("Sem temporizadores")
        self._empty.show()
        self._list.setObjectName("clockList")
        self._list.setProperty("testid", f"{testid_prefix}-list")
        self._collapsed_icons = QWidget(self)
        self._collapsed_icons.setObjectName("clockCollapsedIcons")
        self._collapsed_icons.setProperty("testid", f"{testid_prefix}-collapsed-icons")
        self._collapsed_icons_layout = QVBoxLayout(self._collapsed_icons)
        self._collapsed_icons_layout.setContentsMargins(0, 0, 0, 0)
        self._collapsed_icons_layout.setSpacing(4)
        self._layout.addWidget(self._collapsed_icons)
        self._collapsed_icons.hide()
        try:
            self.btn_add.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
        self.btn_add.clicked.connect(self._add_timer)
        self._ticker = QTimer(self)
        self._ticker.setInterval(1000)
        self._ticker.timeout.connect(self._tick_timers)
        self._ticker.start()
        self.refresh()

    def set_task(self, task: Task | None) -> None:
        return

    def refresh(self) -> None:
        self._list.clear()
        if self._repo is None:
            self._empty.setText("Sem repositório")
            self._empty.show()
            self._list.hide()
            return
        timers = self._repo.list_clock_timers(self._kind)
        if not timers:
            self._empty.setText("Sem temporizadores")
            self._empty.show()
            self._list.hide()
            return
        timers = sorted(timers, key=lambda t: self._remaining_seconds(t))
        self._empty.hide()
        self._list.show()
        for timer in timers:
            self._add_timer_row(timer)
        self._refresh_collapsed_icons(timers)

    def _add_timer_row(self, timer) -> None:
        item = QListWidgetItem()
        item.setData(_ROLE_SUBTASK_ID, timer.id)
        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        item.setSizeHint(QSize(1, 56))
        self._list.addItem(item)

        remaining = self._remaining_seconds(timer)
        done = remaining <= 0
        card = _ClockTimerCard(timer.id, self._list, testid_prefix=self._testid_prefix)
        card.setProperty("testid", f"{self._testid_prefix}-card-{timer.id}")
        card.setStyleSheet(
            self._timer_card_style(
                "done" if done else "running",
                self._normalize_timer_color(getattr(timer, "color", "")),
            )
        )
        card.clicked.connect(self._edit_timer)
        card.pause_toggled.connect(self._toggle_pause_timer)
        card.delete_requested.connect(self._delete_timer)
        card.restart_requested.connect(self._restart_timer_one_hour)

        card_layout = QVBoxLayout(card.content)
        card_layout.setContentsMargins(10, 3, 10, 3)
        card_layout.setSpacing(0)
        title = QLabel(timer.title, card.content)
        title.setStyleSheet("font-size: 11px; font-weight: 900; color: #F8FAFC;")
        title.setTextFormat(Qt.TextFormat.PlainText)
        time_label = QLabel(self._fmt_hms(remaining), card.content)
        time_label.setProperty("testid", f"{self._testid_prefix}-card-time-{timer.id}")
        time_label.setStyleSheet(
            "font-family: 'JetBrains Mono', 'Ubuntu Mono', monospace; "
            "font-size: 19px; font-weight: 900; letter-spacing: 1px;"
            f"color: {'#052E16' if done else '#FDE68A'};"
        )
        card.pause_btn.setText("▶" if timer.paused and not done else "⏸")
        card.pause_btn.setEnabled(not done)
        card.pause_btn.setVisible(not done)
        card.delete_btn.setVisible(done)
        card.plus_one_btn.setVisible(done)
        card_layout.addWidget(title)
        card_layout.addWidget(time_label)
        self._list.setItemWidget(item, card)

    def _timer_card_style(self, state: str, accent: str = _CLOCK_TIMER_DEFAULT_COLOR) -> str:
        accent = self._normalize_timer_color(accent)
        if state == "done":
            return (
                "QFrame#clockTimerCard {"
                "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #22C55E, stop:1 #15803D);"
                "border: 1px solid #86EFAC;"
                f"border-left: 7px solid {accent};"
                "border-radius: 12px; text-align: left;}"
            )
        return (
            "QFrame#clockTimerCard {"
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #090A0E, stop:1 #1A1508);"
            f"border: 1px solid {self._running_border};"
            f"border-left: 7px solid {accent};"
            "border-radius: 12px; text-align: left;}"
            f"QFrame#clockTimerCard:hover {{ background: #1A160C; border-color: {self._running_hover_border}; }}"
        )

    def _add_timer(self) -> None:
        payload = self._open_timer_dialog(None)
        if payload is None or self._repo is None:
            return
        from task_manager_desktop.core.models import ClockTimer

        ends_at = payload["ends_at"]
        remaining = self._seconds_until_iso(ends_at)
        timer = ClockTimer(
            id=f"tm-{uuid.uuid4().hex[:10]}",
            title=payload["title"],
            duration_seconds=remaining,
            remaining_seconds=remaining,
            ends_at=ends_at,
            color=self._normalize_timer_color(payload["color"]),
            state="running" if remaining > 0 else "done",
            paused=False,
            paused_at=None,
            kind=self._kind,
        )
        self._repo.create_clock_timer(timer)
        self.refresh()

    def _edit_timer(self, timer_id: str) -> None:
        if self._repo is None:
            return
        timers = {t.id: t for t in self._repo.list_clock_timers(self._kind)}
        timer = timers.get(timer_id)
        if timer is None:
            return
        payload = self._open_timer_dialog(timer)
        if payload is None:
            return
        ends_at = payload["ends_at"]
        remaining = self._seconds_until_iso(ends_at)
        timer.title = payload["title"]
        timer.ends_at = ends_at
        timer.color = self._normalize_timer_color(payload["color"])
        timer.duration_seconds = remaining
        timer.remaining_seconds = remaining
        timer.state = "running" if remaining > 0 else "done"
        timer.paused = False
        timer.paused_at = None
        self._repo.update_clock_timer(timer)
        self.refresh()

    def _open_timer_dialog(self, timer) -> dict[str, str] | None:
        from PySide6.QtCore import QDateTime
        from PySide6.QtWidgets import (
            QButtonGroup,
            QCalendarWidget,
            QDateTimeEdit,
            QDialog,
            QTimeEdit,
        )

        dlg = QDialog(self)
        dlg.setWindowTitle("Temporizador")
        dlg.setModal(True)
        dlg.setMinimumWidth(380)
        dlg.setStyleSheet(
            "QDialog { background: #111116; }"
            "QLabel#dlgHead { font-size: 15px; font-weight: 700; color: #F8FAFC; }"
            "QLabel#dlgSec  { font-size: 10px; font-weight: 700; color: #71717A;"
            "                  letter-spacing: 1px; }"
            "QLineEdit {"
            "  background: #1C1D24; border: 1px solid #3B3D46; border-radius: 8px;"
            "  padding: 8px 10px; color: #F8FAFC; font-size: 13px; }"
            "QLineEdit:focus { border-color: #FBBF24; }"
            "QDateTimeEdit {"
            "  background: #1C1D24; border: 1px solid #3B3D46; border-radius: 8px;"
            "  padding: 8px 10px; color: #F8FAFC; font-size: 13px; }"
            "QDateTimeEdit:focus { border-color: #FBBF24; }"
            "QDateTimeEdit::drop-down { width: 0; border: none; }"
            "QToolButton#datePickerBtn {"
            "  background: #1C1D24; border: 1px solid #3B3D46; border-radius: 8px;"
            "  padding: 0; }"
            "QToolButton#datePickerBtn:hover { border-color: #FBBF24; background: #27272A; }"
            "QPushButton#shortBtn {"
            "  background: #1C1D24; border: 1px solid #3B3D46; border-radius: 6px;"
            "  color: #A1A1AA; font-size: 12px; font-weight: 800; padding: 8px 12px; }"
            "QPushButton#shortBtn:hover {"
            "  background: #27272A; border-color: #FBBF24; color: #FBBF24; }"
            "QFrame#durationBox { background: #17181D; border: 1px solid #363942;"
            "  border-radius: 10px; }"
            "QLineEdit#durationInput {"
            "  background: #0D0E12; border: 1px solid #2F3037; border-radius: 8px;"
            "  color: #F8FAFC; font-family: 'JetBrains Mono', 'Ubuntu Mono', monospace;"
            "  font-size: 17px; font-weight: 900; padding: 8px 10px;"
            "  selection-background-color: #FBBF24; selection-color: #0D0E12; }"
            "QLineEdit#durationInput:focus { border-color: #FBBF24; }"
            "QPushButton#colorSwatch { border: 2px solid #363942; border-radius: 10px;"
            "  padding: 0; }"
            "QPushButton#colorSwatch:hover { border-color: #F8FAFC; }"
            "QPushButton#colorSwatch:checked { border-color: #FBBF24; }"
            "QPushButton#okBtn {"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #B45309,stop:1 #FBBF24);"
            "  border: none; border-radius: 8px; color: #0D0E12;"
            "  font-size: 13px; font-weight: 700; padding: 8px 22px; }"
            "QPushButton#okBtn:disabled { background: #27272A; color: #52525B; }"
            "QPushButton#okBtn:hover:!disabled {"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #FBBF24,stop:1 #FDE68A); }"
            "QPushButton#cancelBtn {"
            "  background: transparent; border: 1px solid #3B3D46; border-radius: 8px;"
            "  color: #71717A; font-size: 13px; font-weight: 600; padding: 8px 16px; }"
            "QPushButton#cancelBtn:hover { border-color: #71717A; color: #F8FAFC; }"
            "QLabel#errLabel { color: #F87171; font-size: 11px; }"
            "QFrame#divider { color: #2F3037; background: #2F3037; max-height: 1px; }"
        )

        root = QVBoxLayout(dlg)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(0)

        head = QLabel("Temporizador", dlg)
        head.setObjectName("dlgHead")
        root.addWidget(head)
        root.addSpacing(16)

        lbl_name = QLabel("NOME", dlg)
        lbl_name.setObjectName("dlgSec")
        root.addWidget(lbl_name)
        root.addSpacing(4)
        name = QLineEdit(dlg)
        name.setPlaceholderText("Nome do temporizador")
        root.addWidget(name)
        root.addSpacing(14)

        lbl_dt = QLabel("DATA/HORA FINAL", dlg)
        lbl_dt.setObjectName("dlgSec")
        root.addWidget(lbl_dt)
        root.addSpacing(4)
        dt_row = QHBoxLayout()
        dt_row.setSpacing(8)
        end_dt = QDateTimeEdit(dlg)
        end_dt.setCalendarPopup(True)
        end_dt.setDisplayFormat("dd/MM/yyyy  HH:mm")
        end_dt.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        dt_row.addWidget(end_dt, 1)
        picker_btn = QToolButton(dlg)
        picker_btn.setObjectName("datePickerBtn")
        picker_btn.setProperty("testid", "clock-timer-datetime-picker")
        picker_btn.setAccessibleName("Escolher data e hora finais")
        picker_btn.setToolTip("Escolher data e hora")
        picker_btn.setIcon(svg_to_icon(CLOCK_SVG, 19))
        picker_btn.setIconSize(QSize(19, 19))
        picker_btn.setFixedSize(40, 40)
        picker_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dt_row.addWidget(picker_btn)
        root.addLayout(dt_row)
        root.addSpacing(14)

        divider = QFrame(dlg)
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Plain)
        divider.setLineWidth(1)
        root.addWidget(divider)
        root.addSpacing(14)

        lbl_duration = QLabel("DURAÇÃO", dlg)
        lbl_duration.setObjectName("dlgSec")
        root.addWidget(lbl_duration)
        root.addSpacing(4)
        duration_row = QHBoxLayout()
        duration_row.setSpacing(8)
        duration_input = QLineEdit(dlg)
        duration_input.setObjectName("durationInput")
        duration_input.setProperty("testid", "clock-timer-duration-input")
        duration_input.setAccessibleName("Duração do temporizador em horas, minutos e segundos")
        duration_input.setPlaceholderText("001:00:00")
        duration_input.setMaxLength(9)
        duration_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        duration_input.setText(self._format_duration_text(3600))
        duration_row.addWidget(duration_input, 1)
        shortcut_1d = QPushButton("1d", dlg)
        shortcut_1d.setObjectName("shortBtn")
        shortcut_1d.setProperty("testid", "clock-timer-shortcut-1d")
        shortcut_1d.setCursor(Qt.CursorShape.PointingHandCursor)
        duration_row.addWidget(shortcut_1d)
        shortcut_7d = QPushButton("7d", dlg)
        shortcut_7d.setObjectName("shortBtn")
        shortcut_7d.setProperty("testid", "clock-timer-shortcut-7d")
        shortcut_7d.setCursor(Qt.CursorShape.PointingHandCursor)
        duration_row.addWidget(shortcut_7d)
        root.addLayout(duration_row)
        root.addSpacing(14)

        lbl_color = QLabel("COR DO CARD", dlg)
        lbl_color.setObjectName("dlgSec")
        root.addWidget(lbl_color)
        root.addSpacing(6)
        color_row = QHBoxLayout()
        color_row.setSpacing(8)
        color_group = QButtonGroup(dlg)
        color_group.setExclusive(True)
        selected_color = {"value": _CLOCK_TIMER_DEFAULT_COLOR}
        color_buttons: list[tuple[str, QPushButton]] = []
        for label, color in _CLOCK_TIMER_COLORS:
            swatch = QPushButton(dlg)
            swatch.setObjectName("colorSwatch")
            swatch.setProperty("testid", f"clock-timer-color-{label}")
            swatch.setAccessibleName(f"Cor {label} do temporizador")
            swatch.setToolTip(label.capitalize())
            swatch.setCheckable(True)
            swatch.setFixedSize(34, 34)
            swatch.setCursor(Qt.CursorShape.PointingHandCursor)
            swatch.setStyleSheet(
                "QPushButton#colorSwatch {"
                f"background: {color};"
                "border: 2px solid #363942; border-radius: 10px;"
                "}"
                "QPushButton#colorSwatch:hover { border-color: #F8FAFC; }"
                "QPushButton#colorSwatch:checked { border-color: #FBBF24; }"
            )
            color_group.addButton(swatch)
            color_row.addWidget(swatch)
            color_buttons.append((color, swatch))
        color_row.addStretch(1)
        root.addLayout(color_row)

        err = QLabel("", dlg)
        err.setObjectName("errLabel")
        err.setVisible(False)
        root.addSpacing(4)
        root.addWidget(err)
        root.addSpacing(18)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch(1)
        cancel_btn = QPushButton("✕  Cancelar", dlg)
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn = QPushButton("✓  OK", dlg)
        ok_btn.setObjectName("okBtn")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setDefault(True)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        if timer is not None:
            name.setText(timer.title)
            parsed = self._parse_iso(timer.ends_at)
            if parsed is not None:
                end_dt.setDateTime(QDateTime.fromSecsSinceEpoch(int(parsed.timestamp())))
            selected_color["value"] = self._normalize_timer_color(getattr(timer, "color", ""))

        for color, swatch in color_buttons:
            if color == selected_color["value"]:
                swatch.setChecked(True)
                break
        else:
            color_buttons[0][1].setChecked(True)

        syncing = {"value": False}

        def _set_duration_seconds(seconds: int) -> None:
            seconds = max(1, int(seconds))
            syncing["value"] = True
            try:
                end_dt.setDateTime(QDateTime.currentDateTime().addSecs(seconds))
                duration_input.setText(self._format_duration_text(seconds))
            finally:
                syncing["value"] = False
            _validate()

        def _sync_duration_from_end() -> None:
            if syncing["value"]:
                return
            seconds = self._seconds_until_iso(end_dt.dateTime().toUTC().toString(Qt.DateFormat.ISODate))
            duration_input.setText(self._format_duration_text(seconds))

        def _apply_duration_input() -> None:
            seconds = self._parse_duration_text(duration_input.text())
            if seconds is not None and seconds > 0:
                _set_duration_seconds(seconds)
            else:
                _validate()

        def _open_picker() -> None:
            picker = QDialog(dlg)
            picker.setWindowTitle("Escolher data e hora")
            picker.setModal(True)
            picker.setMinimumWidth(330)
            picker.setStyleSheet(dlg.styleSheet())
            picker_layout = QVBoxLayout(picker)
            picker_layout.setContentsMargins(18, 18, 18, 18)
            picker_layout.setSpacing(12)
            calendar = QCalendarWidget(picker)
            calendar.setSelectedDate(end_dt.dateTime().date())
            picker_layout.addWidget(calendar)
            time_edit = QTimeEdit(picker)
            time_edit.setDisplayFormat("HH:mm:ss")
            time_edit.setTime(end_dt.dateTime().time())
            time_edit.setStyleSheet(
                "QTimeEdit { background: #1C1D24; border: 1px solid #3B3D46;"
                "border-radius: 8px; padding: 8px 10px; color: #F8FAFC;"
                "font-size: 14px; }"
            )
            picker_layout.addWidget(time_edit)
            picker_buttons = QHBoxLayout()
            picker_buttons.addStretch(1)
            picker_cancel = QPushButton("Cancelar", picker)
            picker_cancel.setObjectName("cancelBtn")
            picker_ok = QPushButton("OK", picker)
            picker_ok.setObjectName("okBtn")
            picker_buttons.addWidget(picker_cancel)
            picker_buttons.addWidget(picker_ok)
            picker_layout.addLayout(picker_buttons)
            picker_cancel.clicked.connect(picker.reject)
            picker_ok.clicked.connect(picker.accept)
            if picker.exec() == int(QDialog.DialogCode.Accepted):
                end_dt.setDateTime(
                    QDateTime(calendar.selectedDate(), time_edit.time())
                )
                _sync_duration_from_end()
                _validate()

        def _validate() -> bool:
            title_ok = bool(name.text().strip())
            end_iso = end_dt.dateTime().toUTC().toString(Qt.DateFormat.ISODate)
            sec = self._seconds_until_iso(end_iso)
            dt_ok = sec > 0
            duration_ok = (self._parse_duration_text(duration_input.text()) or 0) > 0
            if not dt_ok:
                end_dt.setStyleSheet(
                    "QDateTimeEdit { border-color: #F87171; background: #1C0A0A; }"
                )
                err.setText("⚠  Escolha uma data/hora no futuro.")
                err.setVisible(True)
            elif not duration_ok:
                duration_input.setStyleSheet(
                    "QLineEdit#durationInput { border-color: #F87171; background: #1C0A0A; }"
                )
                err.setText("⚠  Informe a duração no formato hhh:mm:ss.")
                err.setVisible(True)
            else:
                end_dt.setStyleSheet("")
                duration_input.setStyleSheet("")
                err.setVisible(False)
            ok_btn.setEnabled(title_ok and dt_ok and duration_ok)
            return title_ok and dt_ok and duration_ok

        cancel_btn.clicked.connect(dlg.reject)
        ok_btn.clicked.connect(dlg.accept)
        picker_btn.clicked.connect(_open_picker)
        shortcut_1d.clicked.connect(lambda: _set_duration_seconds(24 * 3600))
        shortcut_7d.clicked.connect(lambda: _set_duration_seconds(7 * 24 * 3600))
        color_group.buttonClicked.connect(
            lambda button: selected_color.update(
                value=next(
                    color for color, swatch in color_buttons if swatch is button
                )
            )
        )
        name.textChanged.connect(lambda _t: _validate())
        end_dt.dateTimeChanged.connect(lambda _t: (_sync_duration_from_end(), _validate()))
        duration_input.textChanged.connect(lambda _t: _validate())
        duration_input.editingFinished.connect(_apply_duration_input)
        duration_input.returnPressed.connect(_apply_duration_input)
        _sync_duration_from_end()
        _validate()

        if dlg.exec() != int(QDialog.DialogCode.Accepted):
            return None
        title = name.text().strip()
        ends_at = end_dt.dateTime().toUTC().toString(Qt.DateFormat.ISODate)
        if not title or self._seconds_until_iso(ends_at) <= 0:
            return None
        return {
            "title": title,
            "ends_at": ends_at,
            "color": self._normalize_timer_color(selected_color["value"]),
        }

    @staticmethod
    def _normalize_timer_color(color: str) -> str:
        return color if color in _CLOCK_TIMER_COLOR_VALUES else _CLOCK_TIMER_DEFAULT_COLOR

    @staticmethod
    def _parse_duration_text(text: str) -> int | None:
        value = text.strip()
        parts = value.split(":")
        if len(parts) != 3:
            return None
        if len(parts[0]) > 3 or any(len(part) != 2 for part in parts[1:]):
            return None
        try:
            hours, minutes, seconds = (int(part) for part in parts)
        except ValueError:
            return None
        if hours > 999 or minutes > 59 or seconds > 59:
            return None
        total = hours * 3600 + minutes * 60 + seconds
        return total if total > 0 else None

    @staticmethod
    def _format_duration_text(total_seconds: int) -> str:
        total_seconds = max(0, int(total_seconds))
        hours = min(999, total_seconds // 3600)
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:03d}:{minutes:02d}:{seconds:02d}"

    def _fmt_hms(self, total_seconds: int) -> str:
        total_seconds = max(0, int(total_seconds))
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h:03d}:{m:02d}:{s:02d}"

    def _tick_timers(self) -> None:
        if self._repo is None:
            return
        try:
            timers = self._repo.list_clock_timers(self._kind)
        except Exception as exc:  # noqa: BLE001 - timer de UI nao deve vazar excecao Qt
            _log.debug("clock.tick_stopped: %s", exc)
            self._ticker.stop()
            return
        for timer in timers:
            remaining = self._remaining_seconds(timer)
            if timer.paused or timer.state == "done":
                continue
            if remaining <= 0 and timer.state != "done":
                timer.remaining_seconds = 0
                timer.state = "done"
                timer.paused = False
                timer.paused_at = None
                self._repo.update_clock_timer(timer)
        # sempre atualiza view para o contador visual avançar.
        self.refresh()

    def _toggle_pause_timer(self, timer_id: str) -> None:
        if self._repo is None:
            return
        timers = {t.id: t for t in self._repo.list_clock_timers(self._kind)}
        timer = timers.get(timer_id)
        if timer is None or self._remaining_seconds(timer) <= 0:
            return
        now_iso = datetime.now(timezone.utc).isoformat()
        if not timer.paused:
            timer.paused = True
            timer.paused_at = now_iso
            timer.remaining_seconds = self._remaining_seconds(timer)
        else:
            if timer.paused_at:
                paused_at = self._parse_iso(timer.paused_at)
                if paused_at is not None:
                    delta = datetime.now(timezone.utc) - paused_at
                    ends = self._parse_iso(timer.ends_at)
                    if ends is not None:
                        timer.ends_at = (ends + delta).isoformat()
            timer.paused = False
            timer.paused_at = None
        self._repo.update_clock_timer(timer)
        self.refresh()

    def _delete_timer(self, timer_id: str) -> None:
        if self._repo is None:
            return
        timers = {t.id: t for t in self._repo.list_clock_timers(self._kind)}
        timer = timers.get(timer_id)
        if timer is None or self._remaining_seconds(timer) > 0:
            return
        self._repo.delete_clock_timer(timer_id)
        self.refresh()

    def _restart_timer_one_hour(self, timer_id: str) -> None:
        if self._repo is None:
            return
        timers = {t.id: t for t in self._repo.list_clock_timers(self._kind)}
        timer = timers.get(timer_id)
        # Só reinicia temporizadores já finalizados (botão +1 só aparece no done).
        if timer is None or self._remaining_seconds(timer) > 0:
            return
        one_hour = 3600
        ends_at = (datetime.now(timezone.utc) + timedelta(seconds=one_hour)).isoformat()
        timer.duration_seconds = one_hour
        timer.remaining_seconds = one_hour
        timer.ends_at = ends_at
        timer.state = "running"
        timer.paused = False
        timer.paused_at = None
        self._repo.update_clock_timer(timer)
        self.refresh()

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self.btn_toggle.setText("[>]" if collapsed else "[<]")
        self.btn_toggle.setAccessibleName(
            "Expandir painel de clock" if collapsed else "Colapsar painel de clock"
        )
        self._layout.setContentsMargins(*(_COLLAPSED_MARGINS if collapsed else _EXPANDED_MARGINS))
        self._header_layout.setSpacing(6)
        self.btn_add.setVisible(not collapsed)
        self.btn_show_all.setVisible(False)
        self.btn_clear_done.setVisible(False)
        self._body_title.setVisible(not collapsed)
        if collapsed:
            self._list.hide()
            self._empty.hide()
            self._collapsed_icons.show()
            self._refresh_collapsed_icons()
        else:
            self._collapsed_icons.hide()
            # retorna ao fluxo padrao de renderizacao expandida
            self.refresh()
        collapsed_width = self.collapsed_width()
        target_width = collapsed_width if collapsed else _EXPANDED_WIDTH
        self.setMinimumWidth(target_width)
        self.setMaximumWidth(target_width)
        self.updateGeometry()

    def _refresh_collapsed_icons(self, timers: list | None = None) -> None:
        while self._collapsed_icons_layout.count():
            item = self._collapsed_icons_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        if timers is None and self._repo is not None:
            timers = self._repo.list_clock_timers(self._kind)
        timers = timers or []
        active = [t for t in timers if self._remaining_seconds(t) > 0]
        if not active:
            hint = QLabel("·", self._collapsed_icons)
            hint.setStyleSheet("color: #3F3F46; font-size: 18px; font-weight: 900;")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._collapsed_icons_layout.addWidget(hint)
            return
        for timer in active:
            icon = QLabel("⏱", self._collapsed_icons)
            icon.setProperty("testid", f"{self._testid_prefix}-collapsed-icon-{timer.id}")
            icon.setToolTip(timer.title)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setStyleSheet("color: #FBBF24; font-size: 16px; font-weight: 900;")
            self._collapsed_icons_layout.addWidget(icon)

    def _parse_iso(self, value: str) -> datetime | None:
        if not value:
            return None
        # Python 3.10 fromisoformat rejeita o sufixo "Z" gerado pelo Qt ISODate.
        normalized = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _seconds_until_iso(self, value: str) -> int:
        end = self._parse_iso(value)
        if end is None:
            return 0
        now = datetime.now(timezone.utc)
        return max(0, int((end - now).total_seconds()))

    def _remaining_seconds(self, timer) -> int:
        if timer.paused:
            return max(0, int(timer.remaining_seconds))
        return self._seconds_until_iso(timer.ends_at)


class _ClockTimerCard(QFrame):
    clicked = Signal(str)
    pause_toggled = Signal(str)
    delete_requested = Signal(str)
    restart_requested = Signal(str)

    def __init__(
        self,
        timer_id: str,
        parent: QWidget | None = None,
        *,
        testid_prefix: str = "clock",
    ) -> None:
        super().__init__(parent)
        self._timer_id = timer_id
        self.setObjectName("clockTimerCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.content = QWidget(self)
        root.addWidget(self.content, 1)
        controls = QVBoxLayout()
        controls.setContentsMargins(0, 2, 4, 2)
        controls.setSpacing(2)
        self.delete_btn = QToolButton(self)
        self.delete_btn.setObjectName("clockDeleteBtn")
        self.delete_btn.setProperty("testid", f"{testid_prefix}-card-delete-{timer_id}")
        self.delete_btn.setAccessibleName("Excluir temporizador finalizado")
        self.delete_btn.setToolTip("Excluir temporizador finalizado")
        self.delete_btn.setText("×")
        self.delete_btn.setFixedSize(26, 22)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self._timer_id))
        self.pause_btn = QToolButton(self)
        self.pause_btn.setObjectName("clockPauseBtn")
        self.pause_btn.setProperty("testid", f"{testid_prefix}-card-pause-{timer_id}")
        self.pause_btn.setFixedSize(26, 26)
        self.pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_btn.clicked.connect(lambda: self.pause_toggled.emit(self._timer_id))
        self.plus_one_btn = QToolButton(self)
        self.plus_one_btn.setObjectName("clockPlusOneBtn")
        self.plus_one_btn.setProperty("testid", f"{testid_prefix}-card-plus-one-{timer_id}")
        self.plus_one_btn.setAccessibleName("Reiniciar com 1 hora")
        self.plus_one_btn.setToolTip("Iniciar nova contagem de 1 hora")
        self.plus_one_btn.setText("+1")
        self.plus_one_btn.setFixedSize(34, 26)
        self.plus_one_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.plus_one_btn.setStyleSheet(
            "QToolButton#clockPlusOneBtn {"
            "background: #052E16; color: #BBF7D0;"
            "border: 1px solid #166534; border-radius: 7px;"
            "font-size: 12px; font-weight: 900; }"
            "QToolButton#clockPlusOneBtn:hover {"
            "background: #166534; color: #F0FDF4; }"
        )
        self.plus_one_btn.clicked.connect(lambda: self.restart_requested.emit(self._timer_id))
        controls.addWidget(self.delete_btn, 0, Qt.AlignmentFlag.AlignRight)
        controls.addStretch(1)
        controls.addWidget(self.plus_one_btn, 0, Qt.AlignmentFlag.AlignRight)
        controls.addWidget(self.pause_btn, 0, Qt.AlignmentFlag.AlignRight)
        root.addLayout(controls)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._timer_id)
        super().mousePressEvent(event)


class SubtaskClockPane(QWidget):
    """Container da coluna central: SubtaskPane (55%) + área de timers (45%).

    A área de timers é dividida em duas divs independentes empilhadas:
    Daily Timers (35%, borda verde) em cima e Timers (65%, borda amarela)
    embaixo. Cada div lista/cria apenas o seu ``kind`` de timer.
    """

    def __init__(self, repo: TaskRepository | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("subtaskClockPane")
        self.setAccessibleName("Painel de subtasks e clock")
        self.setProperty("testid", "subtask-clock-pane")
        self.subtasks_section = QWidget(self)
        self.subtasks_section.setObjectName("subtasksSection")
        self.subtasks_section.setProperty("testid", "subtasks-pane")
        self.subtasks_section_layout = QVBoxLayout(self.subtasks_section)
        self.subtasks_section_layout.setContentsMargins(0, 0, 0, 0)
        self.subtasks_section_layout.setSpacing(0)
        self.subtask_pane = SubtaskPane(repo=repo, parent=self.subtasks_section)
        self.subtasks_section_layout.addWidget(self.subtask_pane)

        # Div nova (superior): Daily Timers — clone da ClockPane com kind="daily",
        # borda verde nos cards e data-testids próprios (daily-clock-*).
        self.daily_clock_pane = ClockPane(
            repo=repo,
            parent=self,
            kind="daily",
            title="Daily Timers",
            pane_testid="daily-clock-pane",
            testid_prefix="daily-clock",
            accessible_name="Painel de daily timers",
            running_border="#22C55E",
            running_hover_border="#4ADE80",
        )
        # Div original (inferior): Timers — kind="normal", borda amarela.
        self.clock_pane = ClockPane(repo=repo, parent=self)
        self.btn_toggle = self.subtask_pane.btn_toggle
        self.clock_pane.btn_toggle.hide()
        self.daily_clock_pane.btn_toggle.hide()

        self._divider = QFrame(self)
        self._divider.setObjectName("subtaskClockDivider")
        self._divider.setProperty("testid", "subtask-clock-divider")
        self._divider.setFrameShape(QFrame.Shape.HLine)
        self._divider.setFrameShadow(QFrame.Shadow.Plain)
        self._divider.setLineWidth(1)
        self._divider.setStyleSheet("QFrame#subtaskClockDivider { color: #52525B; background: #52525B; }")

        # Área de timers: container com as duas divs empilhadas 35/65.
        self.timers_section = QWidget(self)
        self.timers_section.setObjectName("timersSection")
        self.timers_section.setProperty("testid", "timers-pane")
        timers_layout = QVBoxLayout(self.timers_section)
        timers_layout.setContentsMargins(0, 0, 0, 0)
        timers_layout.setSpacing(6)

        self._timers_divider = QFrame(self.timers_section)
        self._timers_divider.setObjectName("dailyTimersDivider")
        self._timers_divider.setProperty("testid", "daily-timers-divider")
        self._timers_divider.setFrameShape(QFrame.Shape.HLine)
        self._timers_divider.setFrameShadow(QFrame.Shadow.Plain)
        self._timers_divider.setLineWidth(1)
        self._timers_divider.setStyleSheet(
            "QFrame#dailyTimersDivider { color: #52525B; background: #52525B; }"
        )

        timers_layout.addWidget(self.daily_clock_pane, 35)
        timers_layout.addWidget(self._timers_divider, 0)
        timers_layout.addWidget(self.clock_pane, 65)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.subtasks_section, 55)
        layout.addWidget(self._divider, 0)
        layout.addWidget(self.timers_section, 45)

        # Trava a largura do container (coluna 2) no mesmo limite das panes
        # internas. Sem isto o QSplitter estica o container proporcionalmente a
        # janela (_apply_splitter_ratios usa total_w * ratio) e a coluna 2 cresce
        # alem de _EXPANDED_WIDTH conforme a janela aumenta.
        self.setMinimumWidth(_EXPANDED_WIDTH)
        self.setMaximumWidth(_EXPANDED_WIDTH)

    def collapsed_width(self) -> int:
        return self.subtask_pane.collapsed_width()

    def set_collapsed(self, collapsed: bool) -> None:
        self.subtask_pane.set_collapsed(collapsed)
        self.daily_clock_pane.set_collapsed(collapsed)
        self.clock_pane.set_collapsed(collapsed)
        self.timers_section.setVisible(not collapsed)
        # Mantem a largura da coluna 2 travada no limite (colapsada ou nao),
        # independente da largura da janela.
        target_width = self.collapsed_width() if collapsed else _EXPANDED_WIDTH
        self.setMinimumWidth(target_width)
        self.setMaximumWidth(target_width)
        self.updateGeometry()

    def set_task(self, task: Task | None) -> None:
        self.subtask_pane.set_task(task)
        self.daily_clock_pane.set_task(task)
        self.clock_pane.set_task(task)

    def set_type_filter(self, task_types: object) -> None:
        """Encaminha o filtro de tipo do header apenas para a pane de subtasks.

        A ClockPane lista temporizadores (sem tipo agent/dev/human), entao o
        filtro nao se aplica a ela.
        """
        self.subtask_pane.set_type_filter(task_types)

    def set_on_subtasks_changed(self, callback: Callable[[], None] | None) -> None:
        """Encaminha o callback de mudanca de subtasks apenas para a pane de subtasks."""
        self.subtask_pane.set_on_subtasks_changed(callback)
