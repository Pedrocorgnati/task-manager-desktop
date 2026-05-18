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
        1 for dep_id in deps if dep_id in all_tasks and all_tasks[dep_id].status != Status.DONE
    )


def has_open_deps_for(task: Task, all_tasks: dict[str, Task]) -> bool:
    """True se a task tem >=1 dep ativa (status != done).

    IDs invalidos em task.deps (dep deletada) sao silenciosamente
    ignorados — espelhando US-001 cenario 4 (orfaos pos-delete).
    """
    for dep_id in task.deps:
        dep = all_tasks.get(dep_id)
        if dep is None:
            continue  # ID invalido — ignorar silenciosamente
        if dep.status != Status.DONE:
            return True
    return False


def compute_sector_change_propagation(
    changed_task_id: str,
    all_tasks: dict[str, Task],
) -> list[tuple[str, Sector, Color]]:
    """Calcula novo setor/cor para dependentes DIRETOS de changed_task_id.

    Apenas um nivel — nao recursivo (D-006 / US-005 cenario 4).
    A propria task changed_task_id NAO esta no resultado.

    Returns:
        Lista de (dependent_task_id, new_sector, new_color).
        Vazia se nenhuma task tem changed_task_id em suas deps.
    """
    result: list[tuple[str, Sector, Color]] = []
    for tid, task in all_tasks.items():
        if tid == changed_task_id:
            continue
        if changed_task_id not in task.deps:
            continue
        if task.status == Status.DONE:
            continue
        has_open = has_open_deps_for(task, all_tasks)
        new_sector, new_color = compute_sector(task.status, has_open)
        result.append((tid, new_sector, new_color))
    return result


__all__ = [
    "compute_sector",
    "compute_sector_change_propagation",
    "count_open_deps",
    "has_open_deps_for",
]
