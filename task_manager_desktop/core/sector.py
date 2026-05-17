from __future__ import annotations

from task_manager_desktop.core.models import Color, Sector, Status, Task


def compute_sector(status: Status, has_open_deps: bool) -> tuple[Sector, Color]:
    if status == Status.DONE:
        return Sector.DONE, Color.NEUTRAL
    if status == Status.IN_PROGRESS:
        return Sector.ACTIVE, Color.GRAY if has_open_deps else Color.GREEN
    # PENDING
    if has_open_deps:
        return Sector.BLOCKED, Color.GRAY
    return Sector.WAITING, Color.YELLOW


def count_open_deps(deps: list[str], all_tasks: dict[str, Task]) -> int:
    return sum(
        1
        for dep_id in deps
        if dep_id in all_tasks and all_tasks[dep_id].status != Status.DONE
    )


__all__ = ["compute_sector", "count_open_deps"]
