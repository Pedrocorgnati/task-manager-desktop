from __future__ import annotations

import sqlite3

import pytest

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.exceptions import TaskNotFoundError
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


@pytest.fixture
def sample_task(repo) -> Task:
    task = Task(
        id="task-abc-001",
        title="Tarefa de teste",
        status=Status.PENDING,
        type=TaskType.ONLINE,
        projeto="outros",
        deps=[],
        notes="# Notas originais",
        order_index=0,
    )
    repo.create(task)
    return task


def test_update_notes_persists(repo, sample_task):
    repo.update_notes(sample_task.id, "# Updated")
    result = repo.get_by_id(sample_task.id)
    assert result is not None
    assert result.notes == "# Updated"


def test_update_notes_accepts_empty(repo, sample_task):
    repo.update_notes(sample_task.id, "")
    result = repo.get_by_id(sample_task.id)
    assert result is not None
    assert result.notes == ""


def test_update_notes_raises_when_not_found(repo):
    with pytest.raises(TaskNotFoundError):
        repo.update_notes("nonexistent-id", "x")
