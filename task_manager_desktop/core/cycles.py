from __future__ import annotations

from task_manager_desktop.core.models import Task


def _has_path(
    start: str,
    target: str,
    all_tasks: dict[str, Task],
) -> list[str] | None:
    """DFS iterativo. Retorna o caminho start->...->target ou None."""
    if start == target:
        return [start]
    stack = [(start, [start])]
    visited: set[str] = set()
    while stack:
        node, path = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        if node not in all_tasks:
            continue
        for dep in all_tasks[node].deps:
            if dep == target:
                return path + [dep]
            if dep not in visited:
                stack.append((dep, path + [dep]))
    return None


def resolve_cycles(
    task_id: str,
    proposed_deps: list[str],
    all_tasks: dict[str, Task],
) -> tuple[list[str], str | None]:
    # Drop self-references and IDs absent from all_tasks
    filtered = [d for d in proposed_deps if d != task_id and d in all_tasks]

    safe: list[str] = []
    description: str | None = None

    for dep in filtered:
        path = _has_path(dep, task_id, all_tasks)
        if path is not None:
            if description is None:
                cycle_path = "->".join(path)
                description = (
                    f"Substituida dep '{dep}' para evitar ciclo com '{cycle_path}'"
                )
        else:
            safe.append(dep)

    return safe, description


__all__ = ["resolve_cycles"]
