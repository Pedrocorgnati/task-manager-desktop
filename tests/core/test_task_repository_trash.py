from __future__ import annotations

import pytest

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository


@pytest.fixture
def repo(in_memory_db):
    run_migrations(in_memory_db)
    return TaskRepository(in_memory_db, db_path=":memory:")


def _mk(
    tid: str,
    *,
    status: Status = Status.PENDING,
    title: str = "T",
    order_index: int = 0,
) -> Task:
    return Task(
        id=tid,
        title=title,
        status=status,
        type=TaskType.HUMAN,
        deps=[],
        notes="",
        order_index=order_index,
        created_at="2026-05-17T10:00:00",
    )


def test_hide_all_done_marks_only_done_tasks(repo):
    repo.create(_mk("a", status=Status.DONE))
    repo.create(_mk("b", status=Status.PENDING, order_index=1))
    repo.create(_mk("c", status=Status.IN_PROGRESS, order_index=2))

    n = repo.hide_all_done()

    assert n == 1
    assert repo.get_by_id("a").hidden_at is not None
    assert repo.get_by_id("b").hidden_at is None
    assert repo.get_by_id("c").hidden_at is None


def test_hide_all_done_returns_zero_when_no_done(repo):
    repo.create(_mk("a", status=Status.PENDING))
    assert repo.hide_all_done() == 0


def test_hide_all_done_skips_already_hidden(repo):
    repo.create(_mk("a", status=Status.DONE))
    repo.hide_all_done()
    # Second call should mark zero — already hidden
    assert repo.hide_all_done() == 0


def test_hide_all_done_excludes_already_hidden_from_active(repo):
    repo.create(_mk("a", status=Status.DONE))
    repo.create(_mk("b", status=Status.PENDING, order_index=1))
    repo.hide_all_done()

    active_ids = [t.id for t in repo.list_active()]
    trash_ids = [t.id for t in repo.list_trash()]
    assert "a" not in active_ids
    assert "a" in trash_ids
    assert "b" in active_ids


def test_restore_clears_hidden_at(repo):
    repo.create(_mk("a", status=Status.DONE))
    repo.hide_all_done()
    assert repo.get_by_id("a").hidden_at is not None

    repo.restore("a")
    assert repo.get_by_id("a").hidden_at is None
    assert "a" in [t.id for t in repo.list_active()]


def test_restore_preserves_status(repo):
    """Restore restores hidden_at to NULL but does NOT change status."""
    repo.create(_mk("a", status=Status.DONE))
    repo.hide_all_done()
    repo.restore("a")
    assert repo.get_by_id("a").status == Status.DONE


def test_hide_all_done_batches_in_single_transaction(repo):
    for i, status in enumerate(
        [Status.DONE, Status.DONE, Status.PENDING, Status.DONE]
    ):
        repo.create(_mk(f"t{i}", status=status, order_index=i))

    n = repo.hide_all_done()
    assert n == 3
    assert len(repo.list_trash()) == 3
