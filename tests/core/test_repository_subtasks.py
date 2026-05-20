from __future__ import annotations

import sqlite3

import pytest

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Subtask, Task
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


def test_delete_done_subtasks_removes_only_state_2_from_task(repo):
    repo.create(Task(id="a", title="A"))
    repo.create(Task(id="b", title="B"))
    repo.create_subtask(Subtask(id="a0", task_id="a", text="A0", state=0))
    repo.create_subtask(Subtask(id="a1", task_id="a", text="A1", state=1))
    repo.create_subtask(Subtask(id="a2", task_id="a", text="A2", state=2))
    repo.create_subtask(Subtask(id="b2", task_id="b", text="B2", state=2))

    removed = repo.delete_done_subtasks("a")

    assert removed == 1
    assert [s.id for s in repo.list_subtasks("a")] == ["a0", "a1"]
    assert [s.id for s in repo.list_subtasks("b")] == ["b2"]


def test_delete_done_subtasks_returns_zero_when_group_has_no_done(repo):
    repo.create(Task(id="a", title="A"))
    repo.create_subtask(Subtask(id="a0", task_id="a", text="A0", state=0))

    assert repo.delete_done_subtasks("a") == 0


def test_subtask_notes_are_created_listed_and_updated(repo):
    repo.create(Task(id="a", title="A"))
    repo.create_subtask(Subtask(id="a0", task_id="a", text="A0", notes="inicial"))

    assert repo.list_subtasks("a")[0].notes == "inicial"

    repo.update_subtask_notes("a0", "autosave")

    assert repo.list_subtasks("a")[0].notes == "autosave"
