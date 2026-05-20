from __future__ import annotations

from task_manager_desktop.core.filters import (
    is_active,
    matches,
)
from task_manager_desktop.core.models import Status, Task, TaskType


def _make_task(
    title: str = "task",
    notes: str = "",
    task_type: TaskType = TaskType.HUMAN,
) -> Task:
    return Task(
        id="t1",
        title=title,
        status=Status.PENDING,
        type=task_type,
        deps=[],
        notes=notes,
        order_index=1,
        created_at="2026-05-17T10:00:00",
    )


def test_default_type_filter_passes():
    assert matches(_make_task())


def test_task_type_filter_includes_selected_types():
    human = _make_task(task_type=TaskType.HUMAN)
    dev = _make_task(task_type=TaskType.DEV)
    agent = _make_task(task_type=TaskType.AGENT)
    assert matches(human, task_types={"human", "dev"})
    assert matches(dev, task_types={"human", "dev"})
    assert not matches(agent, task_types={"human", "dev"})


def test_is_active_detects_type_filter():
    assert is_active(task_types={"human", "agent"})
    assert is_active(task_types=set())


def test_is_active_false_when_default_filters():
    assert not is_active()
    assert not is_active(task_types={t.value for t in TaskType})
