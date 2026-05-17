from __future__ import annotations

import sqlite3

from PySide6.QtCore import QObject

from task_manager_desktop.core.models import Task
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.dialogs import ErrorDialog
from task_manager_desktop.ui.task_list import TaskList


class DeleteTaskController(QObject):
    def __init__(
        self,
        repo: TaskRepository,
        task_list: TaskList,
        main_window: QObject,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self._task_list = task_list
        self._main_window = main_window

    def handle(self, task: Task) -> None:
        from PySide6.QtWidgets import QWidget

        parent_widget = self._main_window if isinstance(self._main_window, QWidget) else None
        db_path = self._repo.db_path
        try:
            self._repo.delete(task.id)
        except sqlite3.Error as exc:
            ErrorDialog.show_io_error(parent_widget, exc, db_path)
            return

        remaining = self._repo.list_active()
        self._task_list.refresh(remaining)

        # Reset viewer if the deleted task was selected (RF-AC-T-003)
        current_id = getattr(self._main_window, "_current_task_id", None)
        if current_id == task.id and hasattr(self._main_window, "reset_viewer_to_empty"):
            self._main_window.reset_viewer_to_empty()
