from __future__ import annotations

from collections.abc import Iterable

from task_manager_desktop.core.models import Task, TaskType

ALL_TASK_TYPES: frozenset[str] = frozenset(t.value for t in TaskType)


def _normalize_type_filter(task_types: Iterable[str | TaskType] | None) -> frozenset[str]:
    if task_types is None:
        return ALL_TASK_TYPES
    return frozenset(
        item.value if isinstance(item, TaskType) else str(item)
        for item in task_types
    )


def matches(
    task: Task,
    task_types: Iterable[str | TaskType] | None = None,
) -> bool:
    allowed_types = _normalize_type_filter(task_types)
    if task.type.value not in allowed_types:
        return False

    return True


def is_active(
    task_types: Iterable[str | TaskType] | None = None,
) -> bool:
    if _normalize_type_filter(task_types) != ALL_TASK_TYPES:
        return True
    return False


__all__ = ["ALL_TASK_TYPES", "matches", "is_active"]
