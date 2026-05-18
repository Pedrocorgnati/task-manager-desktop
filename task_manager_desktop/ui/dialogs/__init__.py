from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ErrorDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        description: str,
        path: str,
        suggestion: str,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(400, 200)
        self.setModal(True)
        self.setAccessibleName(title)
        self.setAccessibleDescription(description)
        self._path = path

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(12)

        desc_label = QLabel(description, self)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        path_label = QLabel(f"Caminho: {path}", self)
        path_label.setWordWrap(True)
        path_label.setProperty("secondary", True)
        layout.addWidget(path_label)

        sug_label = QLabel(suggestion, self)
        sug_label.setWordWrap(True)
        sug_label.setProperty("muted", True)
        layout.addWidget(sug_label)

        btn_box = QDialogButtonBox(self)
        ok_btn = btn_box.addButton(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setDefault(True)
        ok_btn.setAutoDefault(True)
        btn_box.accepted.connect(self.accept)

        self._copy_btn = QPushButton("Copiar caminho", self)
        btn_box.addButton(self._copy_btn, QDialogButtonBox.ButtonRole.ActionRole)
        self._copy_btn.clicked.connect(self._on_copy)

        layout.addWidget(btn_box)

    def _on_copy(self) -> None:
        QApplication.clipboard().setText(self._path)
        self._copy_btn.setText("Copiado!")
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._copy_btn.setText("Copiar caminho"))
        timer.start(1500)

    @classmethod
    def show_io_error(
        cls,
        parent: QWidget | None,
        exception: BaseException,
        db_path: str,
    ) -> int:
        dlg = cls(
            parent=parent,
            title="Erro de I/O",
            description=repr(exception),
            path=db_path,
            suggestion="Verifique espaço em disco e permissões de escrita.",
        )
        return dlg.exec()


from task_manager_desktop.ui.dialogs.edit_task_dialog import EditTaskDialog  # noqa: E402
from task_manager_desktop.ui.dialogs.task_form_widget import TaskFormWidget  # noqa: E402
from task_manager_desktop.ui.dialogs.trash_dialog import TrashDialog  # noqa: E402

__all__ = ["EditTaskDialog", "ErrorDialog", "TaskFormWidget", "TrashDialog"]
