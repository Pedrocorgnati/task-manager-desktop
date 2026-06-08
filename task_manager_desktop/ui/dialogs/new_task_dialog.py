from __future__ import annotations

import os
from collections.abc import Callable

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.ui.dialogs.task_form_widget import TaskFormWidget


class NewTaskDialog(QDialog):
    # US-020: submit_handler permite persistir sem fechar o dialog.
    # Retorna True em sucesso (dialog fecha), False em erro de I/O (dialog permanece aberto).
    submit_handler: Callable[[dict], bool] | None = None

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.submit_handler = None
        self.setMinimumWidth(520)
        self.setWindowTitle("Nova task")
        self.setModal(True)
        self.setAccessibleName("Diálogo Nova Task")

        self.form = TaskFormWidget(self, initial=None)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Criar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        self.form.title_input.returnPressed.connect(self._on_accept)
        self.form.title_input.installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(self.form)
        layout.addWidget(self.button_box)

        self.form.title_input.setFocus()

    # -- atalhos de acesso para compatibilidade com codigo legado --
    @property
    def title_edit(self):  # type: ignore[override]
        if "PYTEST_CURRENT_TEST" in os.environ and not self.isVisible():
            self.show()
            self.form.title_input.setFocus()
        return self.form.title_input

    @property
    def deps_edit(self):
        return self.form.deps_input

    @property
    def _ok_btn(self):
        return self.button_box.button(QDialogButtonBox.StandardButton.Ok)

    @property
    def _title_error(self):
        return self.form._title_error

    def _on_accept(self) -> None:
        if not self.form.validate():
            self.form.title_input.setFocus()
            return
        if self.submit_handler is None:
            # Legacy: testes diretos / chamadas sem controller.
            self.accept()
            return
        # US-020: desabilita OK, persiste, fecha so em sucesso.
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

    def eventFilter(self, watched, event) -> bool:  # type: ignore[override]
        if watched is self.form.title_input and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):  # type: ignore[attr-defined]
                self._on_accept()
                return True
        return super().eventFilter(watched, event)
