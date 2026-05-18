from __future__ import annotations

import sqlite3
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from task_manager_desktop.core.models import Status, Task
from task_manager_desktop.core.sector import compute_sector_change_propagation
from task_manager_desktop.repositories.task_repository import TaskRepository

_PROPAGATION_THRESHOLD = 20


class ChangeStatusController:
    """Pure-logic controller for status transitions.

    Accepts Protocol-based dependencies so unit tests run without Qt.
    The app wire-up passes adapters; tests pass mocks.
    """

    def __init__(
        self,
        repo: TaskRepository,
        all_tasks_provider: Callable[[], dict[str, Task]],
        error_handler: object,
        refresh_card: Callable[[Task], None],
        task_list: Any | None = None,
    ) -> None:
        self._repo = repo
        self._all_tasks = all_tasks_provider
        self._errors = error_handler
        self._refresh_card = refresh_card
        self._task_list = task_list
        self._busy = False

    def change_status(self, task: Task, new_status_str: str, segmented: object | None = None) -> None:
        """Primary entry-point.  segmented is optional; when provided its
        setEnabled(bool) / setValue(str) are called to prevent double-click
        and to revert the visual on I/O error."""

        # Re-entrancy guard: fast double-click protection
        if self._busy:
            return

        # Defensive status conversion
        try:
            new_status = Status(new_status_str)
        except ValueError:
            print(f"[WARN] invalid status {new_status_str!r}", file=sys.stderr)
            return

        # No-op: same status clicked
        if task.status == new_status:
            return

        # completed_at logic (AC-T-002)
        # _completed_dt is a datetime object passed to update_status; stored as ISO str in Task
        if new_status == Status.DONE:
            _completed_dt: datetime | None = datetime.now(timezone.utc).replace(tzinfo=None)
        elif task.status == Status.DONE:
            _completed_dt = None
        else:
            _completed_dt = None  # preserve existing value by re-reading from DB after update

        previous_status = task.status

        # Lock UI against double-click
        if segmented is not None:
            segmented.setEnabled(False)  # type: ignore[attr-defined]
        self._busy = True
        try:
            self._repo.update_status(task.id, new_status, _completed_dt)
        except (sqlite3.OperationalError, sqlite3.IntegrityError, Exception) as exc:
            self._errors.show_io_error(str(exc), self._repo.db_path)  # type: ignore[attr-defined]
            if segmented is not None:
                segmented.setValue(previous_status.value)  # type: ignore[attr-defined]
            self._refresh_card(task)  # task still holds previous status in memory
            return
        finally:
            self._busy = False
            if segmented is not None:
                segmented.setEnabled(True)  # type: ignore[attr-defined]

        # Success: mutate in-memory task, trigger refresh
        task.status = new_status
        if new_status == Status.DONE:
            task.completed_at = _completed_dt.isoformat() if _completed_dt else None
        elif previous_status == Status.DONE:
            task.completed_at = None
        # else: keep existing completed_at (no-change transitions)
        self._refresh_card(task)

        # Propagacao de dependentes diretos (RF-008 / US-005)
        # Apenas em sucesso; nao em path de erro (AC-T-008)
        if self._task_list is None:
            return

        all_tasks = self._all_tasks()
        propagation = compute_sector_change_propagation(task.id, all_tasks)

        if not propagation:
            return

        if len(propagation) >= _PROPAGATION_THRESHOLD:
            self._task_list.refresh()
            return

        for dep_id, new_sector, _new_color in propagation:
            self._task_list.move_card_to_sector(dep_id, new_sector)

    def handle(self, task: Task, new_status_str: str, segmented: object | None = None) -> None:
        """Backward-compatible alias used by app.py callbacks dict."""
        self.change_status(task, new_status_str, segmented)
