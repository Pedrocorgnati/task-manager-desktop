from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.task_list import TaskList


@pytest.fixture
def repo(in_memory_db):
    run_migrations(in_memory_db)
    return TaskRepository(in_memory_db, db_path=":memory:")


def _make_task(
    repo: TaskRepository,
    *,
    tid: str,
    title: str,
    status: Status = Status.PENDING,
    order_index: int = 1,
) -> Task:
    t = Task(
        id=tid,
        title=title,
        status=status,
        type=TaskType.HUMAN,
        deps=[],
        notes="",
        order_index=order_index,
        created_at="2026-05-18T10:00:00",
    )
    repo.create(t)
    return t


def _build_task_list(qtbot, repo) -> TaskList:
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())
    return tl


# ------------------------------------------------------------------
# Down arrow
# ------------------------------------------------------------------


def test_down_selects_first_task_when_no_selection(qtbot, repo):
    _make_task(repo, tid="t1", title="task one")
    _make_task(repo, tid="t2", title="task two", order_index=2)
    tl = _build_task_list(qtbot, repo)

    assert not tl.has_selection()
    qtbot.keyClick(tl._inner, Qt.Key.Key_Down)
    assert tl.has_selection()


def test_down_moves_to_next_task(qtbot, repo):
    _make_task(repo, tid="t1", title="first")
    _make_task(repo, tid="t2", title="second", order_index=2)
    tl = _build_task_list(qtbot, repo)

    tl._inner.setCurrentRow(tl._task_rows()[0])
    qtbot.keyClick(tl._inner, Qt.Key.Key_Down)

    selected = tl.get_selected_task()
    assert selected is not None
    assert selected.id == "t2"


def test_down_at_last_task_stays(qtbot, repo):
    _make_task(repo, tid="t1", title="only task")
    tl = _build_task_list(qtbot, repo)

    rows = tl._task_rows()
    tl._inner.setCurrentRow(rows[-1])
    initial_row = tl._inner.currentRow()
    qtbot.keyClick(tl._inner, Qt.Key.Key_Down)
    assert tl._inner.currentRow() == initial_row


# ------------------------------------------------------------------
# Up arrow
# ------------------------------------------------------------------


def test_up_moves_to_prev_task(qtbot, repo):
    _make_task(repo, tid="t1", title="first")
    _make_task(repo, tid="t2", title="second", order_index=2)
    tl = _build_task_list(qtbot, repo)

    rows = tl._task_rows()
    tl._inner.setCurrentRow(rows[1])  # select t2
    qtbot.keyClick(tl._inner, Qt.Key.Key_Up)

    selected = tl.get_selected_task()
    assert selected is not None
    assert selected.id == "t1"


def test_up_at_first_task_stays(qtbot, repo):
    _make_task(repo, tid="t1", title="only task")
    tl = _build_task_list(qtbot, repo)

    rows = tl._task_rows()
    tl._inner.setCurrentRow(rows[0])
    initial_row = tl._inner.currentRow()
    qtbot.keyClick(tl._inner, Qt.Key.Key_Up)
    assert tl._inner.currentRow() == initial_row


# ------------------------------------------------------------------
# Separator skipping
# ------------------------------------------------------------------


def test_down_skips_separator_across_sectors(qtbot, repo):
    """Down from last task in one sector jumps over separator to first task of next."""
    _make_task(repo, tid="t1", title="active", status=Status.IN_PROGRESS)
    _make_task(repo, tid="t2", title="pending", order_index=2)
    tl = _build_task_list(qtbot, repo)

    rows = tl._task_rows()
    tl._inner.setCurrentRow(rows[0])
    first_id = tl.get_selected_task().id  # type: ignore[union-attr]

    qtbot.keyClick(tl._inner, Qt.Key.Key_Down)
    second_id = tl.get_selected_task().id  # type: ignore[union-attr]

    assert second_id != first_id


# ------------------------------------------------------------------
# Enter / Return
# ------------------------------------------------------------------


def test_enter_emits_enter_pressed_on_selection(qtbot, repo):
    _make_task(repo, tid="t1", title="my task")
    tl = _build_task_list(qtbot, repo)

    tl._inner.setCurrentRow(tl._task_rows()[0])
    with qtbot.waitSignal(tl.enter_pressed_on_selection, timeout=500) as blocker:
        qtbot.keyClick(tl._inner, Qt.Key.Key_Return)

    assert blocker.args[0].id == "t1"


def test_return_also_emits_enter_pressed_on_selection(qtbot, repo):
    _make_task(repo, tid="t1", title="my task")
    tl = _build_task_list(qtbot, repo)

    tl._inner.setCurrentRow(tl._task_rows()[0])
    with qtbot.waitSignal(tl.enter_pressed_on_selection, timeout=500) as blocker:
        qtbot.keyClick(tl._inner, Qt.Key.Key_Enter)

    assert blocker.args[0].id == "t1"


def test_enter_without_selection_does_not_emit(qtbot, repo):
    _make_task(repo, tid="t1", title="my task")
    tl = _build_task_list(qtbot, repo)

    tl._inner.clearSelection()
    tl._inner.setCurrentRow(-1)

    received: list[Task] = []
    tl.enter_pressed_on_selection.connect(received.append)
    qtbot.keyClick(tl._inner, Qt.Key.Key_Return)
    qtbot.wait(50)
    assert received == []
