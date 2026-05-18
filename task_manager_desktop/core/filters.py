from __future__ import annotations

from task_manager_desktop.core.models import Task

ALL_PROJECTS_SENTINEL = "__all__"


def matches(task: Task, query: str | None, projeto: str | None) -> bool:
    if projeto and projeto != ALL_PROJECTS_SENTINEL:
        if (task.projeto or "").casefold() != projeto.casefold():
            return False

    if query:
        needle = query.strip().casefold()
        if needle:
            haystack = f"{task.title or ''}\n{task.notes or ''}".casefold()
            if needle not in haystack:
                return False

    return True


def is_active(query: str | None, projeto: str | None) -> bool:
    if query and query.strip():
        return True
    if projeto and projeto != ALL_PROJECTS_SENTINEL:
        return True
    return False


__all__ = ["ALL_PROJECTS_SENTINEL", "matches", "is_active"]
