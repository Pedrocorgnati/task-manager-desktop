from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QApplication

from task_manager_desktop.core.cycles import resolve_cycles
from task_manager_desktop.core.id_gen import generate_id
from task_manager_desktop.core.models import Status, Task
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.dialogs import ErrorDialog
from task_manager_desktop.ui.dialogs.new_task_dialog import NewTaskDialog
from task_manager_desktop.ui.task_list import TaskList
from task_manager_desktop.ui.toast import ToastWidget


class CreateTaskController(QObject):
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

    def handle(self) -> None:
        from PySide6.QtWidgets import QDialog, QWidget

        parent_widget = self._main_window if isinstance(self._main_window, QWidget) else None
        dialog = NewTaskDialog(parent_widget)
        persisted = [False]

        def submit(data: dict) -> bool:
            persisted[0] = True
            return self._persist(data, parent_widget)

        dialog.submit_handler = submit
        result = dialog.exec()
        # Compatibilidade com fakes legados que retornam Accepted sem invocar submit_handler.
        if result == QDialog.DialogCode.Accepted and not persisted[0]:
            self._persist(dialog.get_data(), parent_widget)

    def _persist(self, data: dict, parent_widget) -> bool:
        # US-020 c3: retornar False mantem dialog aberto pra nova tentativa.
        all_tasks = self._repo.list_active()
        all_tasks_dict = {t.id: t for t in all_tasks}

        try:
            conn = self._repo._conn
            task_id = generate_id(conn)
        except RuntimeError as exc:
            ErrorDialog.show_io_error(parent_widget, exc, "")
            return False

        clean_deps, cycle_desc = resolve_cycles(task_id, data["deps"], all_tasks_dict)

        task = Task(
            id=task_id,
            title=data["title"],
            status=Status.PENDING,
            type=data["type"],
            projeto=data["projeto"],
            deps=clean_deps,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._repo.create(task)
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

        self._task_list.refresh(self._repo.list_active())
        return True
