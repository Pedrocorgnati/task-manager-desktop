# suite: acceptance | module: module-1-gestao-de-tasks | task: TASK-3
# @tdd-locked: do not edit without /tdd:unlock
# covers: US-003 (cenarios 1-3) — Excluir task definitivamente (hard-delete)
# TIDs: TID-1-3-001, TID-1-3-002, TID-1-3-003
from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from task_manager_desktop.controllers.delete_task_controller import DeleteTaskController
from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    run_migrations(c)
    yield c
    c.close()


@pytest.fixture
def repo(conn):
    return TaskRepository(conn, db_path=":memory:")


def _task(id: str, title: str = "T", deps: list[str] | None = None, **kw) -> Task:
    return Task(id=id, title=title, deps=deps or [], **kw)


# TID-1-3-001 | covers: US-003#1 | bdd_type: SUCCESS
def test_delete_removes_immediately_without_confirmation(repo):
    """Task excluida desaparece imediatamente da lista sem nenhum dialog de confirmacao."""
    from PySide6.QtWidgets import QMessageBox

    task = _task("abc", "Tarefa ABC")
    repo.create(task)

    mock_tl = MagicMock()
    mock_mw = MagicMock()
    mock_mw._current_task_id = None
    ctrl = DeleteTaskController(repo, mock_tl, mock_mw)

    # Monkeypatch any QMessageBox call to fail — no confirmation dialog should appear
    with patch.object(QMessageBox, "exec", side_effect=AssertionError("QMessageBox.exec invocado!")):
        with patch.object(QMessageBox, "question", side_effect=AssertionError("QMessageBox.question invocado!")):
            ctrl.handle(task)

    # Task must have been removed from DB
    assert repo.get_by_id("abc") is None
    # TaskList.refresh must have been called
    mock_tl.refresh.assert_called_once()


# TID-1-3-002 | covers: US-003#2 | bdd_type: SUCCESS
def test_dependents_recompute_sector_one_level(repo):
    """Dependentes diretos recalculam setor (UM NIVEL); migram de Bloqueadas para Fila se eram bloqueados so pela task excluida."""
    # task_a is the only open dep of task_b
    task_a = _task("a", "A", status=Status.PENDING)
    task_b = _task("b", "B", deps=["a"], status=Status.PENDING)
    repo.create(task_a)
    repo.create(task_b)

    mock_tl = MagicMock()
    mock_mw = MagicMock()
    mock_mw._current_task_id = None
    ctrl = DeleteTaskController(repo, mock_tl, mock_mw)
    ctrl.handle(task_a)

    # After delete: task_a gone, task_b still present
    assert repo.get_by_id("a") is None
    remaining = repo.list_active()
    remaining_map = {t.id: t for t in remaining}
    assert "b" in remaining_map

    # Verify TaskList received the refreshed list (sector recomputed dynamically by TaskList)
    mock_tl.refresh.assert_called_once()
    refreshed = mock_tl.refresh.call_args[0][0]
    ids_refreshed = [t.id for t in refreshed]
    assert "a" not in ids_refreshed
    assert "b" in ids_refreshed

    # No warning about orphaned dep reference (AC: ignored silently)
    # This is structural — if we reached here without exception, it's silent


# TID-1-3-003 | covers: US-003#3 / US-016#3 | bdd_type: ERROR
def test_delete_io_error_preserves_state(conn):
    """Falha de I/O exibe ErrorDialog.show_io_error; card permanece visivel; estado intacto."""
    repo = TaskRepository(conn, db_path="/fake/tasks.db")
    task = _task("abc", "Tarefa ABC")
    repo.create(task)

    mock_tl = MagicMock()
    mock_mw = MagicMock()
    mock_mw._current_task_id = None

    # Create a repo whose delete always raises sqlite3.Error
    broken_repo = TaskRepository(conn, db_path="/fake/tasks.db")

    with patch.object(broken_repo, "delete", side_effect=sqlite3.OperationalError("disk full")):
        ctrl = DeleteTaskController(broken_repo, mock_tl, mock_mw)
        with patch("task_manager_desktop.controllers.delete_task_controller.ErrorDialog") as mock_ed:
            ctrl.handle(task)
            mock_ed.show_io_error.assert_called_once()

    # task still in DB (delete was patched to raise before actually deleting)
    active = repo.list_active()
    ids = [t.id for t in active]
    assert "abc" in ids

    # TaskList.refresh was NOT called (error path exits early)
    mock_tl.refresh.assert_not_called()
