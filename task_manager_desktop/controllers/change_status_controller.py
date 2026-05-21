from __future__ import annotations

import logging
import os
import sqlite3
from collections.abc import Callable
from datetime import datetime

from task_manager_desktop.controllers._protocols import (
    ErrorHandler,
    SegmentedControlLike,
    TaskListLike,
)
from task_manager_desktop.core._time import utc_naive_now
from task_manager_desktop.core.constants import PROPAGATION_THRESHOLD
from task_manager_desktop.core.exceptions import TaskNotFoundError
from task_manager_desktop.core.models import Status, Task
from task_manager_desktop.core.sector import compute_sector_change_propagation
from task_manager_desktop.repositories.task_repository import TaskRepository

_logger = logging.getLogger(__name__)


class ChangeStatusController:
    """Pure-logic controller for status transitions.

    Accepts Protocol-based dependencies so unit tests run without Qt.
    The app wire-up passes adapters; tests pass mocks.

    The `_busy` flag is a defensive guardrail: in single-thread Qt the real
    double-click guard is `segmented.setEnabled(False)`. `_busy` survives a
    future migration to QThreadPool/async without changing call sites.
    """

    def __init__(
        self,
        repo: TaskRepository,
        all_tasks_provider: Callable[[], dict[str, Task]],
        error_handler: ErrorHandler,
        refresh_card: Callable[[Task], None],
        task_list: TaskListLike | None = None,
    ) -> None:
        self._repo = repo
        self._all_tasks = all_tasks_provider
        self._errors = error_handler
        self._refresh_card = refresh_card
        self._task_list = task_list
        self._busy = False

    def change_status(
        self,
        task: Task,
        new_status_str: str,
        segmented: SegmentedControlLike | None = None,
    ) -> None:
        """Primary entry-point.  segmented is optional; when provided its
        setEnabled(bool) / setValue(str) are called to prevent double-click
        and to revert the visual on I/O error."""

        if self._busy:
            return

        try:
            new_status = Status(new_status_str)
        except ValueError:
            _logger.warning(
                "invalid status string %r for task %s",
                new_status_str,
                task.id,
                extra={"task_id": task.id, "new_status_str": new_status_str},
            )
            return

        if task.status == new_status:
            return

        # completed_at logic (AC-T-002)
        if new_status == Status.DONE:
            _completed_dt: datetime | None = utc_naive_now()
        elif task.status == Status.DONE:
            _completed_dt = None
        else:
            _completed_dt = None  # TODO(module-future): migrar schema para aware UTC, ver _SCOPE-CONTRACT.json

        previous_status = task.status

        if segmented is not None:
            segmented.setEnabled(False)
        self._busy = True
        io_error: sqlite3.DatabaseError | None = None
        not_found_error: TaskNotFoundError | None = None
        try:
            # repo.update_status (apos o hardening do repositorio) levanta
            # TaskNotFoundError quando o UPDATE afeta 0 linhas (rowcount 0) e
            # sqlite3.IntegrityError quando afeta >1 linha (rowcount > 1).
            # IntegrityError e subclasse de sqlite3.DatabaseError — ja coberto
            # pelo ramo io_error.
            self._repo.update_status(task.id, new_status, _completed_dt)
        except TaskNotFoundError as exc:
            not_found_error = exc
        except sqlite3.DatabaseError as exc:
            io_error = exc
        finally:
            self._busy = False
            if segmented is not None:
                segmented.setEnabled(True)

        if not_found_error is not None:
            # A task sumiu do banco (corrida / delecao concorrente). Abortar a
            # mutacao otimista em memoria e a propagacao: tratar uma task
            # sumida como sucesso mascararia uma escrita que nao aconteceu.
            db_label = os.path.basename(self._repo.db_path)
            _logger.warning(
                "update_status abortado: task %s nao encontrada (rowcount 0)",
                task.id,
                extra={"task_id": task.id, "db_path": self._repo.db_path},
            )
            self._errors.show_io_error(str(not_found_error), db_label)
            if segmented is not None:
                segmented.setValue(previous_status.value)
            self._refresh_card(task)
            return

        if io_error is not None:
            db_label = os.path.basename(self._repo.db_path)
            _logger.error(
                "I/O error on update_status for task %s",
                task.id,
                extra={"task_id": task.id, "db_path": self._repo.db_path},
            )
            self._errors.show_io_error(str(io_error), db_label)
            if segmented is not None:
                segmented.setValue(previous_status.value)
            self._refresh_card(task)
            return

        # Success: mutate in-memory task, trigger refresh
        task.status = new_status
        if new_status == Status.DONE:
            task.completed_at = _completed_dt.isoformat() if _completed_dt else None
        elif previous_status == Status.DONE:
            task.completed_at = None
        self._refresh_card(task)

        # Propagacao de dependentes diretos (RF-008 / US-005)
        # Apenas em sucesso; nao em path de erro (AC-T-008 ramo b)
        if self._task_list is None:
            return

        all_tasks = self._all_tasks()
        propagation = compute_sector_change_propagation(task.id, all_tasks)

        if not propagation:
            return

        if len(propagation) >= PROPAGATION_THRESHOLD:
            self._task_list.refresh()
            return

        for dep_id, new_sector, _new_color in propagation:
            self._task_list.move_card_to_sector(dep_id, new_sector)

    def handle(
        self,
        task: Task,
        new_status_str: str,
        segmented: SegmentedControlLike | None = None,
    ) -> None:
        """Backward-compatible alias used by app.py callbacks dict."""
        self.change_status(task, new_status_str, segmented)
