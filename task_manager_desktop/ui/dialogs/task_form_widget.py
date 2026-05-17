from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.core.models import Task, TaskType, normalize_projeto, parse_deps


class TaskFormWidget(QWidget):
    """Widget compartilhado com os 4 campos de criacao/edicao de task."""

    def __init__(self, parent: QWidget | None = None, initial: Task | None = None) -> None:
        super().__init__(parent)
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

        self.radio_online = QRadioButton("Online", type_box)
        self.radio_online.setAccessibleName("Tipo Online")
        self.radio_online.setToolTip("Task que requer conexão com a internet")
        self.radio_online.setChecked(True)

        self.radio_offline = QRadioButton("Offline", type_box)
        self.radio_offline.setAccessibleName("Tipo Offline")
        self.radio_offline.setToolTip("Task que pode ser feita sem internet")

        self._type_group = QButtonGroup(self)
        self._type_group.addButton(self.radio_online)
        self._type_group.addButton(self.radio_offline)
        self._type_group.setExclusive(True)

        type_layout.addWidget(self.radio_online)
        type_layout.addWidget(self.radio_offline)
        type_layout.addStretch()
        layout.addWidget(type_box)

        layout.addWidget(self._field_label("Projeto (opcional)"))
        self.projeto_input = QLineEdit(self)
        self.projeto_input.setPlaceholderText("Projeto (opcional, vazio = outros)")
        self.projeto_input.setAccessibleName('Projeto (opcional, vazio usa "outros")')
        layout.addWidget(self.projeto_input)

        layout.addWidget(self._field_label("Dependências (opcional)"))
        self.deps_input = QLineEdit(self)
        self.deps_input.setPlaceholderText("IDs separados por vírgula, opcional")
        self.deps_input.setAccessibleName("IDs de dependências separados por vírgula")
        self.deps_input.setProperty("mono", True)
        layout.addWidget(self.deps_input)

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text, self)
        lbl.setProperty("class", "field-label")
        return lbl

    def _prefill(self, task: Task) -> None:
        self.title_input.setText(task.title)
        if task.type == TaskType.ONLINE:
            self.radio_online.setChecked(True)
        else:
            self.radio_offline.setChecked(True)
        self.projeto_input.setText(task.projeto)
        self.deps_input.setText(", ".join(task.deps))

    def get_data(self) -> dict[str, Any]:
        task_type = TaskType.ONLINE if self.radio_online.isChecked() else TaskType.OFFLINE
        return {
            "title": self.title_input.text().strip(),
            "type": task_type,
            "projeto": normalize_projeto(self.projeto_input.text().strip()),
            "deps": parse_deps(self.deps_input.text()),
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
