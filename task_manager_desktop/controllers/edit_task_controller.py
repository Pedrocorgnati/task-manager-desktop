from __future__ import annotations

import sqlite3

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication

from task_manager_desktop.core.cycles import resolve_cycles
from task_manager_desktop.core.models import Status, Task
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.dialogs import ErrorDialog
from task_manager_desktop.ui.dialogs.edit_task_dialog import EditTaskDialog
from task_manager_desktop.ui.task_list import TaskList
from task_manager_desktop.ui.toast import ToastWidget


class EditTaskController(QObject):
    projects_changed = Signal()

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

    def handle_edit(self, task: Task) -> None:
        from PySide6.QtWidgets import QDialog, QWidget

        parent_widget = self._main_window if isinstance(self._main_window, QWidget) else None
        dialog = EditTaskDialog(task, parent_widget)
        persisted = [False]

        def submit(data: dict) -> bool:
            persisted[0] = True
            return self._persist(task, data, parent_widget)

        dialog.submit_handler = submit
        result = dialog.exec()
        # Compatibilidade com fakes legados que retornam Accepted sem invocar submit_handler.
        if result == QDialog.DialogCode.Accepted and not persisted[0]:
            self._persist(task, dialog.get_data(), parent_widget)

    def _persist(self, task: Task, data: dict, parent_widget) -> bool:
        # US-020 c3: retornar False mantem dialog aberto pra nova tentativa.
        all_tasks = self._repo.list_active()
        all_tasks_dict = {t.id: t for t in all_tasks}

        clean_deps, cycle_desc = resolve_cycles(task.id, data["deps"], all_tasks_dict)

        old_projeto = task.projeto
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._repo.update(
                task.id,
                title=data["title"],
                type=data["type"],
                projeto=data["projeto"],
                deps=clean_deps,
            )
        except sqlite3.Error as exc:
            ErrorDialog.show_io_error(parent_widget, exc, "")
            return False
        finally:
            QApplication.restoreOverrideCursor()

        if cycle_desc and parent_widget:
            toast = ToastWidget(parent_widget)
            toast.show_message(
                "Ciclo de dependência detectado. Dependência mais antiga removida automaticamente."
            )

        if data["projeto"] != old_projeto:
            self.projects_changed.emit()

        self._task_list.refresh(self._repo.list_active())
        return True

    def handle_status_change(self, task: Task, new_status: str) -> None:
        from PySide6.QtWidgets import QWidget

        parent_widget = self._main_window if isinstance(self._main_window, QWidget) else None
        try:
            completed_at = None
            if new_status == "done":
                from datetime import datetime, timezone

                completed_at = datetime.now(timezone.utc).isoformat()
            self._repo.update(task.id, status=Status(new_status), completed_at=completed_at)
        except sqlite3.Error as exc:
            ErrorDialog.show_io_error(parent_widget, exc, "")
            return

        self._task_list.refresh(self._repo.list_active())
