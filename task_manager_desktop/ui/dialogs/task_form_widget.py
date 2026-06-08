from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.core.models import Status, Task, parse_deps
from task_manager_desktop.ui.icons import (
    CHECK_SVG,
    CLOCK_SVG,
    COIN_FILLED_SVG,
    COIN_OUTLINE_SVG,
    STAR_FILLED_SVG,
    STAR_OUTLINE_SVG,
    STRATEGY_SVG,
    TRASH_SVG,
    svg_to_icon,
)

# SVGs inline para pills sem ícone dedicado no catálogo global.
_PERMANENT_OUTLINE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
    ' stroke="#A1A1AA" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M17 1l4 4-4 4"/>'
    '<path d="M3 11V9a4 4 0 0 1 4-4h14"/>'
    '<path d="M7 23l-4-4 4-4"/>'
    '<path d="M21 13v2a4 4 0 0 1-4 4H3"/>'
    "</svg>"
)
_PERMANENT_FILLED_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
    ' stroke="#7BA7FF" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M17 1l4 4-4 4"/>'
    '<path d="M3 11V9a4 4 0 0 1 4-4h14"/>'
    '<path d="M7 23l-4-4 4-4"/>'
    '<path d="M21 13v2a4 4 0 0 1-4 4H3"/>'
    "</svg>"
)
_PROGRESS_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
    ' stroke="#22C55E" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<polygon points="5 3 19 12 5 21 5 3" fill="#22C55E" fill-opacity="0.25"/>'
    "</svg>"
)
_PROGRESS_OUTLINE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
    ' stroke="#A1A1AA" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<polygon points="5 3 19 12 5 21 5 3"/>'
    "</svg>"
)

_PILL_INACTIVE = (
    "QToolButton {"
    " background: #1A1B22;"
    " border: 1px solid #32343F;"
    " border-radius: 8px;"
    " color: #71717A;"
    " font-size: 12px; font-weight: 600;"
    " padding: 6px 14px 6px 10px;"
    "}"
    "QToolButton:hover {"
    " background: #22232D;"
    " border-color: #4B4E5C;"
    " color: #A1A1AA;"
    "}"
)


def _pill_active_css(bg: str, border: str, color: str) -> str:
    return (
        f"QToolButton {{"
        f" background: {bg};"
        f" border: 1px solid {border};"
        f" border-radius: 8px;"
        f" color: {color};"
        f" font-size: 12px; font-weight: 700;"
        f" padding: 6px 14px 6px 10px;"
        f"}}"
        f"QToolButton:hover {{"
        f" background: {bg};"
        f" border-color: {color};"
        f"}}"
    )


class _TogglePill(QToolButton):
    """Pill toggle com ícone outline/filled e estilo contextual por estado."""

    def __init__(
        self,
        outline_svg: str,
        filled_svg: str,
        label: str,
        active_bg: str,
        active_border: str,
        active_color: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._outline_svg = outline_svg
        self._filled_svg = filled_svg
        self._active_bg = active_bg
        self._active_border = active_border
        self._active_color = active_color

        self.setCheckable(True)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.setText(f"  {label}")
        self.setIconSize(QSize(16, 16))
        self.setFixedHeight(34)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh()
        self.toggled.connect(lambda _: self._refresh())

    def _refresh(self) -> None:
        checked = self.isChecked()
        self.setIcon(svg_to_icon(self._filled_svg if checked else self._outline_svg, 16))
        self.setStyleSheet(
            _pill_active_css(self._active_bg, self._active_border, self._active_color)
            if checked
            else _PILL_INACTIVE
        )


class _StatusPill(QToolButton):
    """Pill de status (exclusive group). Aparência distinta quando selecionada."""

    def __init__(
        self,
        outline_svg: str,
        filled_svg: str,
        label: str,
        active_bg: str,
        active_border: str,
        active_color: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._outline_svg = outline_svg
        self._filled_svg = filled_svg
        self._active_bg = active_bg
        self._active_border = active_border
        self._active_color = active_color

        self.setCheckable(True)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.setText(f"  {label}")
        self.setIconSize(QSize(14, 14))
        self.setFixedHeight(34)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh()
        self.toggled.connect(lambda _: self._refresh())

    def _refresh(self) -> None:
        checked = self.isChecked()
        self.setIcon(svg_to_icon(self._filled_svg if checked else self._outline_svg, 14))
        self.setStyleSheet(
            _pill_active_css(self._active_bg, self._active_border, self._active_color)
            if checked
            else _PILL_INACTIVE
        )


class TaskFormWidget(QWidget):
    """Widget compartilhado com os 4 campos de criacao/edicao de task."""

    def __init__(self, parent: QWidget | None = None, initial: Task | None = None) -> None:
        super().__init__(parent)
        self._creating = initial is None
        self._subtask_rows: list[QLineEdit] = []
        self._build_ui()
        if initial is not None:
            self._prefill(initial)
        self.title_input.textChanged.connect(self.clear_title_error)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # ── Título ────────────────────────────────────────────────────────
        layout.addWidget(self._field_label("Título"))
        self.title_input = QLineEdit(self)
        self.title_input.setPlaceholderText("Título da task")
        self.title_input.setAccessibleName("Título da task")
        self.title_input.setAccessibleDescription("Obrigatório")
        layout.addWidget(self.title_input)

        self._title_error = QLabel("Título obrigatório", self)
        self._title_error.setObjectName("fieldErrorLabel")
        self._title_error.hide()
        layout.addWidget(self._title_error)

        # O tipo (agent/dev/human) nao e mais um atributo da task — cada parte
        # do trabalho e uma subtask com seu proprio tipo (definido na subtask
        # pane). Por isso o seletor de tipo foi removido deste formulario.

        # ── Dependências ──────────────────────────────────────────────────
        layout.addWidget(self._field_label("Dependências (opcional)"))
        self.deps_input = QLineEdit(self)
        self.deps_input.setPlaceholderText("IDs separados por vírgula, opcional")
        self.deps_input.setAccessibleName("IDs de dependências separados por vírgula")
        self.deps_input.setProperty("mono", True)
        layout.addWidget(self.deps_input)

        # ── Favoritos ─────────────────────────────────────────────────────
        layout.addWidget(self._field_label("Favoritos"))
        fav_row = QHBoxLayout()
        fav_row.setContentsMargins(0, 0, 0, 0)
        fav_row.setSpacing(8)

        self._star_pill = _TogglePill(
            outline_svg=STAR_OUTLINE_SVG,
            filled_svg=STAR_FILLED_SVG,
            label="Favoritar",
            active_bg="rgba(251,191,36,0.12)",
            active_border="#FBBF24",
            active_color="#FBBF24",
            parent=self,
        )
        self._star_pill.setObjectName("taskFormFavorito")
        self._star_pill.setProperty("testid", "task-form-favorito")
        self._star_pill.setAccessibleName("Marcar task como favorito")
        self._star_pill.setToolTip("Favoritos aparecem no topo do setor")

        self._coin_pill = _TogglePill(
            outline_svg=COIN_OUTLINE_SVG,
            filled_svg=COIN_FILLED_SVG,
            label="Destaque",
            active_bg="rgba(253,230,138,0.12)",
            active_border="#FDE68A",
            active_color="#FDE68A",
            parent=self,
        )
        self._coin_pill.setObjectName("taskFormCoinFavorito")
        self._coin_pill.setProperty("testid", "task-form-coin-favorito")
        self._coin_pill.setAccessibleName("Marcar task como destaque (moeda)")
        self._coin_pill.setToolTip("Destaque aparecem em primeiro no setor")

        self._permanent_pill = _TogglePill(
            outline_svg=_PERMANENT_OUTLINE_SVG,
            filled_svg=_PERMANENT_FILLED_SVG,
            label="Permanente",
            active_bg="rgba(46,91,186,0.15)",
            active_border="#4A76D8",
            active_color="#7BA7FF",
            parent=self,
        )
        self._permanent_pill.setObjectName("taskFormPermanente")
        self._permanent_pill.setProperty("testid", "task-form-permanente")
        self._permanent_pill.setAccessibleName("Marcar task como permanente")
        self._permanent_pill.setToolTip("Tasks permanentes não somem ao concluir")

        fav_row.addWidget(self._star_pill)
        fav_row.addWidget(self._coin_pill)
        fav_row.addWidget(self._permanent_pill)
        fav_row.addStretch()
        layout.addLayout(fav_row)

        # ── Status inicial (apenas criação) ───────────────────────────────
        if self._creating:
            layout.addWidget(self._field_label("Status inicial"))
            status_row = QHBoxLayout()
            status_row.setContentsMargins(0, 0, 0, 0)
            status_row.setSpacing(8)

            self._status_pending_pill = _StatusPill(
                outline_svg=CLOCK_SVG,
                filled_svg=CLOCK_SVG,
                label="Pendente",
                active_bg="rgba(113,113,122,0.18)",
                active_border="#71717A",
                active_color="#D4D4D8",
                parent=self,
            )
            self._status_pending_pill.setObjectName("taskFormStatusPending")
            self._status_pending_pill.setProperty("testid", "task-form-status-pending")
            self._status_pending_pill.setAccessibleName("Status inicial: Pendente")
            self._status_pending_pill.setToolTip("Task inicia como pendente")
            self._status_pending_pill.setChecked(True)

            self._status_progress_pill = _StatusPill(
                outline_svg=_PROGRESS_OUTLINE_SVG,
                filled_svg=_PROGRESS_SVG,
                label="Em progresso",
                active_bg="rgba(22,163,74,0.12)",
                active_border="#22C55E",
                active_color="#4ADE80",
                parent=self,
            )
            self._status_progress_pill.setObjectName("taskFormStatusProgress")
            self._status_progress_pill.setProperty("testid", "task-form-status-progress")
            self._status_progress_pill.setAccessibleName("Status inicial: Em progresso")
            self._status_progress_pill.setToolTip("Task inicia como em progresso")

            # "Em preparação": setor manual verde claro onde a task fica retida
            # enquanto sua estrategia e escrita (flag em_preparacao). Espelha o
            # botao de preparacao do card; nao altera o Status (fica PENDING).
            self._status_prepare_pill = _StatusPill(
                outline_svg=STRATEGY_SVG,
                filled_svg=STRATEGY_SVG,
                label="Em preparação",
                active_bg="rgba(22,163,74,0.16)",
                active_border="#16A34A",
                active_color="#86EFAC",
                parent=self,
            )
            self._status_prepare_pill.setObjectName("taskFormStatusPreparacao")
            self._status_prepare_pill.setProperty("testid", "task-form-status-preparacao")
            self._status_prepare_pill.setAccessibleName("Status inicial: Em preparação")
            self._status_prepare_pill.setToolTip("Task inicia retida em Em preparação")

            self._status_group = QButtonGroup(self)
            self._status_group.addButton(self._status_pending_pill, 0)
            self._status_group.addButton(self._status_progress_pill, 1)
            self._status_group.addButton(self._status_prepare_pill, 2)
            self._status_group.setExclusive(True)

            status_row.addWidget(self._status_pending_pill)
            status_row.addWidget(self._status_progress_pill)
            status_row.addWidget(self._status_prepare_pill)
            layout.addLayout(status_row)

        # ── Subtasks (apenas criação) ─────────────────────────────────────
        if self._creating:
            self._build_subtask_section(layout)

    def _build_subtask_section(self, layout: QVBoxLayout) -> None:
        layout.addWidget(self._field_label("Subtasks (opcional)"))

        # Zero-Assumido: o tipo (agent/dev/human) vive nas subtasks. As criadas
        # aqui nascem como "agent" e o tipo de cada uma e ajustado depois na pane
        # de subtasks — deixar isso explicito evita a suposicao silenciosa.
        _subtask_hint = QLabel("Tipo (agent/dev/human) definido depois na pane de subtasks", self)
        _subtask_hint.setObjectName("subtaskTypeHint")
        _subtask_hint.setProperty("testid", "subtask-type-hint")
        _subtask_hint.setWordWrap(True)
        _subtask_hint.setStyleSheet("color: #71717A; font-size: 11px;")
        layout.addWidget(_subtask_hint)

        self._subtasks_container = QVBoxLayout()
        self._subtasks_container.setContentsMargins(0, 0, 0, 0)
        self._subtasks_container.setSpacing(8)
        layout.addLayout(self._subtasks_container)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(8)

        self.subtask_input = QLineEdit(self)
        self.subtask_input.setPlaceholderText("Descreva a subtask e confirme")
        self.subtask_input.setAccessibleName("Nova subtask")
        self.subtask_input.setProperty("testid", "subtask-new-input")
        self.subtask_input.installEventFilter(self)

        self.subtask_add_btn = QToolButton(self)
        self.subtask_add_btn.setIcon(svg_to_icon(CHECK_SVG, 16))
        self.subtask_add_btn.setIconSize(QSize(16, 16))
        self.subtask_add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.subtask_add_btn.setAccessibleName("Adicionar subtask")
        self.subtask_add_btn.setToolTip("Adicionar subtask")
        self.subtask_add_btn.setProperty("testid", "subtask-add-btn")
        self.subtask_add_btn.clicked.connect(self._commit_subtask)

        input_row.addWidget(self.subtask_input)
        input_row.addWidget(self.subtask_add_btn)
        layout.addLayout(input_row)

    def _commit_subtask(self) -> None:
        text = self.subtask_input.text().strip()
        if not text:
            return
        self._add_committed_subtask_row(text)
        self.subtask_input.clear()
        self.subtask_input.setFocus()

    def _add_committed_subtask_row(self, text: str) -> None:
        row = QWidget(self)
        row.setProperty("testid", "subtask-item")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        edit = QLineEdit(text, row)
        edit.setReadOnly(True)
        edit.setAccessibleName("Subtask")

        remove_btn = QToolButton(row)
        remove_btn.setIcon(svg_to_icon(TRASH_SVG, 16))
        remove_btn.setIconSize(QSize(16, 16))
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setAccessibleName("Remover subtask")
        remove_btn.setToolTip("Remover subtask")
        remove_btn.clicked.connect(lambda: self._remove_subtask_row(row, edit))

        row_layout.addWidget(edit)
        row_layout.addWidget(remove_btn)
        self._subtasks_container.addWidget(row)
        self._subtask_rows.append(edit)

    def _remove_subtask_row(self, row: QWidget, edit: QLineEdit) -> None:
        if edit in self._subtask_rows:
            self._subtask_rows.remove(edit)
        self._subtasks_container.removeWidget(row)
        row.deleteLater()

    def eventFilter(self, obj: Any, event: QEvent) -> bool:
        if obj is getattr(self, "subtask_input", None) and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._commit_subtask()
                return True
        return super().eventFilter(obj, event)

    def _collect_subtasks(self) -> list[str]:
        if not self._creating:
            return []
        texts = [edit.text().strip() for edit in self._subtask_rows]
        pending = self.subtask_input.text().strip()
        if pending:
            texts.append(pending)
        return [t for t in texts if t]

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text, self)
        lbl.setProperty("class", "field-label")
        return lbl

    def _prefill(self, task: Task) -> None:
        self.title_input.setText(task.title)
        self.deps_input.setText(", ".join(task.deps))
        self._star_pill.setChecked(bool(task.favorito))
        self._permanent_pill.setChecked(bool(task.permanente))

    def get_data(self) -> dict[str, Any]:
        status = Status.PENDING
        em_preparacao = False
        if self._creating and hasattr(self, "_status_progress_pill"):
            if self._status_progress_pill.isChecked():
                status = Status.IN_PROGRESS
            elif self._status_prepare_pill.isChecked():
                # Setor manual ortogonal ao Status: a task fica retida em
                # "Em preparação" mantendo o Status PENDING (compute_sector da
                # prioridade a flag em_preparacao sobre pending/in_progress).
                em_preparacao = True

        return {
            "title": self.title_input.text().strip(),
            "deps": parse_deps(self.deps_input.text()),
            "favorito": self._star_pill.isChecked(),
            "permanente": self._permanent_pill.isChecked(),
            "coin_favorite": self._coin_pill.isChecked(),
            "status": status,
            "em_preparacao": em_preparacao,
            "subtasks": self._collect_subtasks(),
        }

    # ── Compat props para código legado que acessa os checkboxes diretamente ──

    @property
    def favorito_checkbox(self) -> _TogglePill:
        return self._star_pill

    @property
    def permanente_checkbox(self) -> _TogglePill:
        return self._permanent_pill

    def validate(self) -> bool:
        if not self.title_input.text().strip():
            self.mark_title_invalid()
            return False
        self.clear_title_error()
        return True

    def mark_title_invalid(self) -> None:
        self.title_input.setProperty("invalid", True)
        self.title_input.setProperty("class", "field-error")
        self.title_input.style().unpolish(self.title_input)
        self.title_input.style().polish(self.title_input)
        self._title_error.show()
        self.title_input.setToolTip("Título obrigatório")
        self.title_input.setFocus()

    def clear_title_error(self) -> None:
        self.title_input.setProperty("invalid", None)
        self.title_input.setProperty("class", None)
        self.title_input.style().unpolish(self.title_input)
        self.title_input.style().polish(self.title_input)
        self._title_error.hide()
        self.title_input.setToolTip("")
