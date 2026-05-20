from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.core.models import Task, TaskType, parse_deps
from task_manager_desktop.ui.icons import CHECK_SVG, TRASH_SVG, svg_to_icon


class TaskFormWidget(QWidget):
    """Widget compartilhado com os 4 campos de criacao/edicao de task."""

    def __init__(self, parent: QWidget | None = None, initial: Task | None = None) -> None:
        super().__init__(parent)
        # Subtasks so podem ser criadas no modal de nova task (modo criacao).
        self._creating = initial is None
        self._subtask_rows: list[QLineEdit] = []
        self._build_ui()
        if initial is not None:
            self._prefill(initial)
        self.title_input.textChanged.connect(self.clear_title_error)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

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

        layout.addWidget(self._field_label("Tipo"))
        type_box = QGroupBox(self)
        type_box.setFlat(True)
        type_box.setStyleSheet("QGroupBox { border: none; padding: 0; margin: 0; }")
        type_layout = QHBoxLayout(type_box)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(16)

        self.radio_agent = QRadioButton("Agent", type_box)
        self.radio_agent.setAccessibleName("Tipo Agent")
        self.radio_agent.setToolTip("Task executada por agente")
        self.radio_agent.setChecked(True)

        self.radio_dev = QRadioButton("Dev", type_box)
        self.radio_dev.setAccessibleName("Tipo Dev")
        self.radio_dev.setToolTip("Task executada por desenvolvedor")

        self.radio_human = QRadioButton("Human", type_box)
        self.radio_human.setAccessibleName("Tipo Human")
        self.radio_human.setToolTip("Task executada por uma pessoa")

        self._type_group = QButtonGroup(self)
        self._type_group.addButton(self.radio_agent)
        self._type_group.addButton(self.radio_dev)
        self._type_group.addButton(self.radio_human)
        self._type_group.setExclusive(True)

        type_layout.addWidget(self.radio_agent)
        type_layout.addWidget(self.radio_dev)
        type_layout.addWidget(self.radio_human)
        type_layout.addStretch()
        layout.addWidget(type_box)

        layout.addWidget(self._field_label("Dependências (opcional)"))
        self.deps_input = QLineEdit(self)
        self.deps_input.setPlaceholderText("IDs separados por vírgula, opcional")
        self.deps_input.setAccessibleName("IDs de dependências separados por vírgula")
        self.deps_input.setProperty("mono", True)
        layout.addWidget(self.deps_input)

        if self._creating:
            self._build_subtask_section(layout)

    def _build_subtask_section(self, layout: QVBoxLayout) -> None:
        """Secao opcional ao final do form: confirma cada subtask com o check
        e abre um novo input em branco para a proxima."""
        layout.addWidget(self._field_label("Subtasks (opcional)"))

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
        """Confirma a subtask digitada: adiciona uma linha e limpa o input."""
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
        # Enter no input de subtask confirma a subtask em vez de submeter o dialog.
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
        if task.type == TaskType.AGENT:
            self.radio_agent.setChecked(True)
        elif task.type == TaskType.DEV:
            self.radio_dev.setChecked(True)
        else:
            self.radio_human.setChecked(True)
        self.deps_input.setText(", ".join(task.deps))

    def get_data(self) -> dict[str, Any]:
        if self.radio_agent.isChecked():
            task_type = TaskType.AGENT
        elif self.radio_dev.isChecked():
            task_type = TaskType.DEV
        else:
            task_type = TaskType.HUMAN
        return {
            "title": self.title_input.text().strip(),
            "type": task_type,
            "deps": parse_deps(self.deps_input.text()),
            "subtasks": self._collect_subtasks(),
        }

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
