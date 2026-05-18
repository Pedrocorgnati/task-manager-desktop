from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.core.filters import ALL_PROJECTS_SENTINEL, is_active, matches
from task_manager_desktop.core.models import Sector, Task
from task_manager_desktop.core.sector import compute_sector, count_open_deps
from task_manager_desktop.ui.theme import PALETTE

if TYPE_CHECKING:
    from task_manager_desktop.repositories.task_repository import TaskRepository

_SECTOR_ORDER = [Sector.ACTIVE, Sector.WAITING, Sector.BLOCKED, Sector.DONE]

_SECTOR_LABELS = {
    Sector.ACTIVE: "— Em execução —",
    Sector.WAITING: "— A fazer —",
    Sector.BLOCKED: "— Bloqueadas —",
    Sector.DONE: "— Concluídas —",
}

_ROLE_TYPE = Qt.ItemDataRole.UserRole + 1  # "separator" | "task" | "placeholder"
_ROLE_TASK_ID = Qt.ItemDataRole.UserRole + 2  # str task id
_ROLE_SECTOR = Qt.ItemDataRole.UserRole + 3  # Sector.value int


def _task_sector(task: Task, all_tasks: dict[str, Task]) -> Sector:
    has_open = count_open_deps(task.deps, all_tasks) > 0
    sector, _ = compute_sector(task.status, has_open)
    return sector


class _InnerList(QListWidget):
    """QListWidget subclass that validates and persists DnD reorder."""

    def __init__(self, outer: TaskList) -> None:
        super().__init__(outer)
        self._outer = outer
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setObjectName("taskListWidget")
        self.setSpacing(2)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _type_at(self, row: int) -> str:
        item = self.item(row)
        return item.data(_ROLE_TYPE) if item else ""

    def _sector_at(self, row: int) -> int:
        item = self.item(row)
        return item.data(_ROLE_SECTOR) if item else 0

    def _task_id_at(self, row: int) -> str:
        item = self.item(row)
        return item.data(_ROLE_TASK_ID) if item else ""

    def _sector_for_row(self, row: int) -> int:
        """Walk backwards to find the separator enclosing this row."""
        for r in range(row, -1, -1):
            if self._type_at(r) == "separator":
                return self._sector_at(r)
        return 0

    def _task_rows_in_sector(self, sector_value: int) -> list[int]:
        return [
            r
            for r in range(self.count())
            if self._type_at(r) == "task" and self._sector_for_row(r) == sector_value
        ]

    # ------------------------------------------------------------------
    # Drag-and-drop
    # ------------------------------------------------------------------

    def dropEvent(self, event: QDropEvent) -> None:
        source_row = self.currentRow()
        if self._type_at(source_row) != "task":
            event.ignore()
            return

        target_item = self.itemAt(event.position().toPoint())
        if target_item is None:
            event.ignore()
            return

        target_row = self.row(target_item)
        target_type = self._type_at(target_row)

        if target_type in ("separator", "placeholder"):
            event.ignore()
            return

        source_sector = self._sector_for_row(source_row)
        target_sector = self._sector_for_row(target_row)

        if source_sector != target_sector:
            event.ignore()
            return

        if source_sector == Sector.DONE.value:
            event.ignore()
            return

        # Snapshot: task ids in sector order before the move
        orig_ids = [self._task_id_at(r) for r in self._task_rows_in_sector(source_sector)]

        # Apply visual move
        super().dropEvent(event)

        # Compute new order after move
        new_ids = [self._task_id_at(r) for r in self._task_rows_in_sector(source_sector)]

        if new_ids == orig_ids:
            return

        new_pairs = [(tid, idx + 1) for idx, tid in enumerate(new_ids)]

        repo = self._outer._repo
        if repo is None:
            return

        try:
            repo.update_order_indexes(new_pairs)
        except sqlite3.OperationalError as exc:
            # Revert visual by full rebuild from stored task list
            self._outer.refresh(self._outer._tasks)
            parent_win = self._outer._main_window
            parent_w = parent_win if isinstance(parent_win, QWidget) else None
            from task_manager_desktop.ui.dialogs import ErrorDialog

            ErrorDialog.show_io_error(parent_w, exc, repo.db_path)
            return

        parent_win = self._outer._main_window
        if isinstance(parent_win, QWidget):
            from task_manager_desktop.ui.toast import ToastWidget

            toast = ToastWidget(parent_win)
            toast.show_info("Ordem atualizada.")


class TaskList(QWidget):
    task_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._callbacks: dict[str, Any] = {}
        self._tasks: list[Task] = []
        self._repo: TaskRepository | None = None
        self._main_window: QWidget | None = None
        self._query: str = ""
        self._projeto: str = ALL_PROJECTS_SENTINEL

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._inner = _InnerList(self)
        layout.addWidget(self._inner)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_callbacks(self, callbacks: dict[str, Any]) -> None:
        self._callbacks = callbacks

    def set_repo(self, repo: TaskRepository) -> None:
        self._repo = repo

    def set_main_window(self, main_window: QWidget) -> None:
        self._main_window = main_window

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self, tasks: list[Task] | None = None) -> None:
        """Rebuild the list.

        If tasks is provided, update the cached list and rebuild.
        If tasks is None, reload from repo (if available) or rebuild from cache.
        """
        if tasks is not None:
            self._tasks = tasks
        elif self._repo is not None:
            self._tasks = self._repo.list_active()
        self._rebuild(self._tasks)

    def set_filters(self, query: str | None, projeto: str | None) -> None:
        self._query = (query or "").strip()
        self._projeto = projeto or ALL_PROJECTS_SENTINEL
        self._rebuild(self._tasks)

    def visible_task_ids(self) -> list[str]:
        return [
            self._inner._task_id_at(r)
            for r in range(self._inner.count())
            if self._inner._type_at(r) == "task"
        ]

    def _task_rows(self) -> list[int]:
        return [
            r
            for r in range(self._inner.count())
            if self._inner._type_at(r) == "task"
        ]

    def move_card_to_sector(self, task_id: str, sector: int) -> None:
        """Move a card to a new sector (incremental render).

        Reloads tasks from repo to get fresh sector assignments for all tasks,
        then rebuilds. No-op if task_id is not found.
        For TASK-3, this will be replaced with a true incremental implementation.
        """
        if self._repo is not None:
            self.refresh(self._repo.list_active())
        else:
            self.refresh()

    # ------------------------------------------------------------------
    # Internal rebuild
    # ------------------------------------------------------------------

    def _rebuild(self, tasks: list[Task]) -> None:
        self._inner.clear()
        all_tasks: dict[str, Task] = {t.id: t for t in tasks}

        filter_active = is_active(self._query, self._projeto)
        visible_tasks = (
            [t for t in tasks if matches(t, self._query, self._projeto)]
            if filter_active
            else list(tasks)
        )

        groups: dict[Sector, list[Task]] = {s: [] for s in _SECTOR_ORDER}
        for task in visible_tasks:
            groups[_task_sector(task, all_tasks)].append(task)
        # Sort each sector by order_index
        for sector_tasks in groups.values():
            sector_tasks.sort(key=lambda t: t.order_index)

        for sector in _SECTOR_ORDER:
            sector_tasks = groups[sector]
            if filter_active and not sector_tasks:
                continue
            self._add_separator(sector)
            if not sector_tasks:
                self._add_placeholder(sector)
            else:
                for task in sector_tasks:
                    self._add_task_item(task, tasks, all_tasks, sector)

    def _add_separator(self, sector: Sector) -> None:
        item = QListWidgetItem(_SECTOR_LABELS[sector])
        item.setData(_ROLE_TYPE, "separator")
        item.setData(_ROLE_SECTOR, sector.value)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setSizeHint(QSize(-1, 32))
        item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._inner.addItem(item)

    def _add_placeholder(self, sector: Sector) -> None:
        item = QListWidgetItem("vazio")
        item.setData(_ROLE_TYPE, "placeholder")
        item.setData(_ROLE_SECTOR, sector.value)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setSizeHint(QSize(-1, 28))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setForeground(QColor(PALETTE["TEXT_MUTED"]))
        self._inner.addItem(item)

    def _add_task_item(
        self,
        task: Task,
        all_tasks_list: list[Task],
        all_tasks_dict: dict[str, Task],
        sector: Sector,
    ) -> None:
        from task_manager_desktop.ui.task_card import TaskCard

        item = QListWidgetItem()
        item.setData(_ROLE_TYPE, "task")
        item.setData(_ROLE_TASK_ID, task.id)
        item.setData(_ROLE_SECTOR, sector.value)
        item.setFlags(
            Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsDragEnabled
            | Qt.ItemFlag.ItemIsDropEnabled
        )
        item.setSizeHint(QSize(-1, 72))
        self._inner.addItem(item)

        card = TaskCard(task, self._callbacks, all_tasks_list, self._inner)
        card.selected.connect(self.task_selected.emit)
        self._inner.setItemWidget(item, card)
