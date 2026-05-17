# suite: acceptance | module: module-1-gestao-de-tasks | task: TASK-3/ST002
# @tdd-locked: do not edit without /tdd:unlock
# covers: US-019 — Reset do viewer ao excluir task selecionada
# TIDs: TID-1-3-004, TID-1-3-005, TID-1-3-006
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


def _task(id: str, title: str = "T") -> Task:
    return Task(id=id, title=title)


# TID-1-3-004 | covers: US-019#1 | bdd_type: SUCCESS
def test_viewer_resets_when_selected_task_deleted(repo):
    """Viewer reseta para empty state quando a task excluida era a selecionada."""
    task = _task("abc", "Tarefa Selecionada")
    repo.create(task)

    mock_tl = MagicMock()
    main_window = MagicMock()
    main_window._current_task_id = "abc"

    ctrl = DeleteTaskController(repo, mock_tl, main_window)
    ctrl.handle(task)

    main_window.reset_viewer_to_empty.assert_called_once()


# TID-1-3-005 | covers: US-019#2 | bdd_type: EDGE
def test_viewer_unaffected_when_other_task_deleted(repo):
    """Viewer permanece intacto quando task excluida nao era a selecionada."""
    task_a = _task("a", "Tarefa A")
    task_b = _task("b", "Tarefa B")
    repo.create(task_a)
    repo.create(task_b)

    mock_tl = MagicMock()
    main_window = MagicMock()
    main_window._current_task_id = "b"  # "b" is selected, but we delete "a"

    ctrl = DeleteTaskController(repo, mock_tl, main_window)
    ctrl.handle(task_a)

    main_window.reset_viewer_to_empty.assert_not_called()


# TID-1-3-006 | covers: US-019#3 | bdd_type: ERROR
def test_io_error_does_not_reset_viewer(repo):
    """I/O error ao excluir a selecionada NAO reseta viewer; conteudo continua presente."""
    task = _task("abc", "Tarefa ABC")
    repo.create(task)

    mock_tl = MagicMock()
    main_window = MagicMock()
    main_window._current_task_id = "abc"

    with patch.object(repo, "delete", side_effect=sqlite3.OperationalError("disk full")):
        ctrl = DeleteTaskController(repo, mock_tl, main_window)
        with patch("task_manager_desktop.controllers.delete_task_controller.ErrorDialog"):
            ctrl.handle(task)

    # Viewer must NOT have been reset because delete failed
    main_window.reset_viewer_to_empty.assert_not_called()
