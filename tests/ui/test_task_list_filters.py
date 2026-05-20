from __future__ import annotations

import pytest

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.task_list import (
    _ROLE_TASK_ID,
    _ROLE_TYPE,
    TaskList,
)


@pytest.fixture
def repo(in_memory_db):
    run_migrations(in_memory_db)
    return TaskRepository(in_memory_db, db_path=":memory:")


def _make_task(
    repo: TaskRepository,
    *,
    tid: str,
    title: str,
    notes: str = "",
    status: Status = Status.PENDING,
    order_index: int = 1,
    task_type: TaskType = TaskType.HUMAN,
) -> Task:
    t = Task(
        id=tid,
        title=title,
        status=status,
        type=task_type,
        deps=[],
        notes=notes,
        order_index=order_index,
        created_at="2026-05-17T10:00:00",
    )
    repo.create(t)
    return t


def _visible_task_ids(task_list: TaskList) -> list[str]:
    inner = task_list._inner
    return [
        inner.item(r).data(_ROLE_TASK_ID)
        for r in range(inner.count())
        if inner.item(r).data(_ROLE_TYPE) == "task"
    ]


def _visible_separators(task_list: TaskList) -> int:
    inner = task_list._inner
    return sum(
        1
        for r in range(inner.count())
        if inner.item(r).data(_ROLE_TYPE) == "separator"
    )


def test_no_filter_shows_all_four_sectors(qtbot, repo):
    _make_task(repo, tid="t1", title="alpha task")
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    assert _visible_separators(tl) == 4
    assert "t1" in _visible_task_ids(tl)


def test_type_filter_filters_by_type(qtbot, repo):
    _make_task(repo, tid="t1", title="human", task_type=TaskType.HUMAN)
    _make_task(repo, tid="t2", title="dev", task_type=TaskType.DEV, order_index=2)
    _make_task(repo, tid="t3", title="agent", task_type=TaskType.AGENT, order_index=3)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.set_filters(task_types={"dev", "agent"})

    assert _visible_task_ids(tl) == ["t2", "t3"]


def test_active_filter_hides_empty_sectors(qtbot, repo):
    # Only an ACTIVE-sector task exists (in_progress), so WAITING/BLOCKED/DONE
    # should be omitted entirely when a filter is active.
    _make_task(
        repo,
        tid="t1",
        title="match me",
        status=Status.IN_PROGRESS,
    )
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.set_filters(task_types={"human"})

    # Exactly one separator (the ACTIVE sector that has the matching task)
    assert _visible_separators(tl) == 1
    assert _visible_task_ids(tl) == ["t1"]


def test_clearing_filter_restores_all_sectors(qtbot, repo):
    _make_task(repo, tid="t1", title="alpha task")
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.set_filters(task_types=set())
    assert _visible_task_ids(tl) == []

    tl.set_filters(task_types={t.value for t in TaskType})
    assert _visible_separators(tl) == 4
    assert _visible_task_ids(tl) == ["t1"]


def test_visible_task_ids_helper(qtbot, repo):
    _make_task(repo, tid="t1", title="alpha task", task_type=TaskType.HUMAN)
    _make_task(repo, tid="t2", title="other", task_type=TaskType.DEV, order_index=2)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.set_filters(task_types={"human"})
    assert tl.visible_task_ids() == ["t1"]


def test_filter_persists_across_refresh(qtbot, repo):
    _make_task(repo, tid="t1", title="human", task_type=TaskType.HUMAN)
    _make_task(repo, tid="t2", title="dev", task_type=TaskType.DEV, order_index=2)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.set_filters(task_types={"human"})
    assert _visible_task_ids(tl) == ["t1"]

    # simulate CRUD refresh (no filter args)
    tl.refresh(repo.list_active())
    # filter must still be active
    assert _visible_task_ids(tl) == ["t1"]


def test_zero_matches_shows_empty_filter_label(qtbot, repo):
    _make_task(repo, tid="t1", title="refactor ui")
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.set_filters(task_types=set())

    # isVisible requires parent hierarchy to be shown; use isHidden instead
    assert not tl._empty_filter_label.isHidden()
    assert tl._empty_label.isHidden()
    assert _visible_task_ids(tl) == []


def test_apply_filter_alias(qtbot, repo):
    _make_task(repo, tid="t1", title="human", task_type=TaskType.HUMAN)
    _make_task(repo, tid="t2", title="dev", task_type=TaskType.DEV, order_index=2)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.apply_filter(task_types={"human"})
    assert _visible_task_ids(tl) == ["t1"]
