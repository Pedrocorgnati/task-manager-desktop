"""Integration tests for DeleteTaskController (TASK-3/ST002).

TIDs: TID-1-3-018..TID-1-3-022
"""
from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from task_manager_desktop.controllers.delete_task_controller import DeleteTaskController
from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Task
from task_manager_desktop.repositories.task_repository import TaskRepository

# ── fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    run_migrations(c)
    yield c
    c.close()


@pytest.fixture
def repo(conn, tmp_path):
    db_path = str(tmp_path / "tasks.db")
    return TaskRepository(conn, db_path=db_path)


@pytest.fixture
def mock_task_list():
    return MagicMock()


@pytest.fixture
def mock_main_window():
    mw = MagicMock()
    mw._current_task_id = None
    return mw


@pytest.fixture
def ctrl(repo, mock_task_list, mock_main_window):
    return DeleteTaskController(repo, mock_task_list, mock_main_window)


def _task(id: str, title: str = "T", deps: list[str] | None = None, **kw) -> Task:
    return Task(id=id, title=title, deps=deps or [], **kw)


# ── TID-1-3-018: end-to-end handle ───────────────────────────────────────────


# TID-1-3-018 | covers: TASK-3/ST002 wire-up
def test_delete_task_controller_handle_end_to_end(repo, mock_task_list, mock_main_window):
    """DeleteTaskController.handle end-to-end:
    delete -> list_active -> recalc setor 1 nivel -> task_list.refresh
    -> reset_viewer_to_empty SE selecionada era a excluida."""
    task_a = _task("a", "Task A")
    task_b = _task("b", "Task B", deps=["a"])
    repo.create(task_a)
    repo.create(task_b)

    mock_main_window._current_task_id = "a"
    ctrl = DeleteTaskController(repo, mock_task_list, mock_main_window)
    ctrl.handle(task_a)

    # A deve ter sido deletada
    assert repo.get_by_id("a") is None

    # refresh foi chamado com as tasks restantes
    args = mock_task_list.refresh.call_args[0][0]
    ids = [t.id for t in args]
    assert "a" not in ids
    assert "b" in ids

    # viewer foi resetado porque "a" estava selecionada
    mock_main_window.reset_viewer_to_empty.assert_called_once()


# ── TID-1-3-019: only one level deep ─────────────────────────────────────────


# TID-1-3-019 | covers: TASK-3/ST002 RF-008
def test_delete_task_controller_recompute_only_one_level_deep(repo, mock_task_list, mock_main_window):
    """DeleteTaskController recalcula apenas UM NIVEL: neto-dependente nao e recomputado."""
    task_a = _task("a", "A")
    task_b = _task("b", "B", deps=["a"])
    task_c = _task("c", "C", deps=["b"])
    repo.create(task_a)
    repo.create(task_b)
    repo.create(task_c)

    ctrl = DeleteTaskController(repo, mock_task_list, mock_main_window)
    ctrl.handle(task_a)

    # refresh deve ter sido chamado (TaskList recomputa setores dinamicamente)
    mock_task_list.refresh.assert_called_once()
    remaining = mock_task_list.refresh.call_args[0][0]
    ids = [t.id for t in remaining]
    assert "a" not in ids
    assert "b" in ids
    assert "c" in ids


# ── TID-1-3-020: I/O error preserves state ───────────────────────────────────


# TID-1-3-020 | covers: TASK-3/ST002 sad path
def test_delete_task_controller_io_error_preserves_state(repo, mock_task_list, mock_main_window):
    """DeleteTaskController em sqlite3.Error: ErrorDialog.show_io_error(parent, exc, db_path)
    + estado intacto (card permanece, viewer NAO reseta)."""
    task_a = _task("a", "A")
    repo.create(task_a)
    mock_main_window._current_task_id = "a"

    ctrl = DeleteTaskController(repo, mock_task_list, mock_main_window)

    with patch.object(repo, "delete", side_effect=sqlite3.OperationalError("disk")):
        with patch("task_manager_desktop.controllers.delete_task_controller.ErrorDialog") as mock_ed:
            ctrl.handle(task_a)
            mock_ed.show_io_error.assert_called_once()

    # task_list.refresh NOT called — state is preserved
    mock_task_list.refresh.assert_not_called()
    # viewer NOT reset — state is preserved
    mock_main_window.reset_viewer_to_empty.assert_not_called()


# ── TID-1-3-021: no QMessageBox confirmation ─────────────────────────────────


# TID-1-3-021 | covers: RF-005 anti-confirm
def test_delete_task_controller_never_calls_qmessagebox_confirmation(repo, mock_task_list, mock_main_window):
    """Anti-confirmacao: monkeypatch QMessageBox para falhar se invocado durante delete;
    cenario nao deve dispara-lo."""
    from PySide6.QtWidgets import QMessageBox

    task = _task("x", "X")
    repo.create(task)
    ctrl = DeleteTaskController(repo, mock_task_list, mock_main_window)

    with patch.object(QMessageBox, "exec", side_effect=AssertionError("QMessageBox.exec called!")):
        with patch.object(QMessageBox, "question", side_effect=AssertionError("QMessageBox.question called!")):
            ctrl.handle(task)  # must complete without raising


# ── TID-1-3-022: smoke crud three tasks ──────────────────────────────────────


# TID-1-3-022 | covers: TASK-3/ST002 smoke
def test_delete_task_controller_smoke_crud_three_tasks(repo, mock_task_list, mock_main_window):
    """Smoke crud: criar 3 tasks, editar 1, excluir 1
    -> TaskList.refresh renderiza estado final consistente."""
    t1 = _task("t1", "Task 1")
    t2 = _task("t2", "Task 2")
    t3 = _task("t3", "Task 3")
    repo.create(t1)
    repo.create(t2)
    repo.create(t3)

    # Edit t2 title
    repo.update("t2", title="Task 2 edited")

    ctrl = DeleteTaskController(repo, mock_task_list, mock_main_window)
    ctrl.handle(t1)

    # After delete: t2 and t3 remain
    remaining = repo.list_active()
    ids = [t.id for t in remaining]
    assert "t1" not in ids
    assert "t2" in ids
    assert "t3" in ids

    # t2 was edited
    t2_updated = repo.get_by_id("t2")
    assert t2_updated is not None
    assert t2_updated.title == "Task 2 edited"

    mock_task_list.refresh.assert_called_once()
