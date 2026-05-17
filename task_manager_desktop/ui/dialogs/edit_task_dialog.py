from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.core.models import Task
from task_manager_desktop.ui.dialogs.task_form_widget import TaskFormWidget


class EditTaskDialog(QDialog):
    # US-020: hook que mantem dialog aberto em erro de I/O.
    submit_handler: Callable[[dict], bool] | None = None

    def __init__(self, task: Task, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._task = task
        self.setMinimumWidth(480)
        self.setWindowTitle("Editar task")
        self.setModal(True)
        self.setAccessibleName("Diálogo Editar Task")

        self.form = TaskFormWidget(self, initial=task)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Salvar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        self.form.title_input.returnPressed.connect(self._on_accept)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(self.form)
        layout.addWidget(self.button_box)

        self.form.title_input.setFocus()

    # -- atalhos de acesso para compatibilidade com codigo legado --
    @property
    def title_edit(self):  # type: ignore[override]
        return self.form.title_input

    @property
    def radio_online(self):
        return self.form.radio_online

    @property
    def radio_offline(self):
        return self.form.radio_offline

    @property
    def project_edit(self):
        return self.form.projeto_input

    @property
    def deps_edit(self):
        return self.form.deps_input

    def _on_accept(self) -> None:
        if not self.form.validate():
            self.form.title_input.setFocus()
            return
        if self.submit_handler is None:
            self.accept()
            return
        self.set_ok_enabled(False)
        try:
            success = bool(self.submit_handler(self.form.get_data()))
        finally:
            if not success:
                self.set_ok_enabled(True)
        if success:
            self.accept()

    def get_data(self) -> dict:
        return self.form.get_data()

    def set_ok_enabled(self, enabled: bool) -> None:
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)
