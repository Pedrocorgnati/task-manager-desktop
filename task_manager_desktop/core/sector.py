from __future__ import annotations

from task_manager_desktop.core.models import Color, Sector, Status, Task

# Cor de destaque (borda azul) do setor PERMANENT. Placeholder ate o design
# publicar o token oficial `accent.permanent` (source.md secao 0, hipotese).
# Trocar este valor NAO deve exigir mudanca em nenhum chamador: compute_sector
# retorna a constante por referencia.
PERMANENT_ACCENT: str = "#2E5BBA"


def compute_sector(
    status: Status,
    has_open_deps: bool,
    permanente: bool = False,
    em_preparacao: bool = False,
) -> tuple[Sector, str]:
    """Setor e cor de destaque canonicos para um status de task.

    Funcao pura: sem side-effect, sem leitura de estado externo.

    Ordem canonica de avaliacao (estrita; nao inverter):
      1. Caminho permanente tem prioridade absoluta dentro de DONE.
      2. DONE nao-permanente.
      3. Flag manual `em_preparacao` (retem a task em EM_PREPARACAO enquanto
         nao concluida), tendo prioridade sobre IN_PROGRESS/PENDING/BLOCKED.
      4. IN_PROGRESS.
      5. Default: PENDING (WAITING ou BLOCKED conforme deps).

    `permanente` so influencia o resultado quando `status == DONE`; com
    qualquer outro status a funcao retorna o setor que retornaria com
    `permanente=False` e nunca consulta `has_open_deps` para essa decisao.
    """
    # 1. Caminho permanente tem prioridade absoluta dentro de DONE.
    if status == Status.DONE and permanente:
        return Sector.PERMANENT, PERMANENT_ACCENT
    # 2. DONE nao-permanente.
    if status == Status.DONE:
        return Sector.DONE, Color.NEUTRAL
    # 3. Setor manual "Em preparação" (so para tasks nao concluidas).
    if em_preparacao:
        return Sector.EM_PREPARACAO, Color.GREEN
    if status == Status.IN_PROGRESS:
        return Sector.ACTIVE, Color.GRAY if has_open_deps else Color.GREEN
    # 3. Default: PENDING.
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
) -> list[tuple[str, Sector, str]]:
    """Calcula novo setor/cor para dependentes DIRETOS de changed_task_id.

    Apenas um nivel — nao recursivo (D-006 / US-005 cenario 4).
    A propria task changed_task_id NAO esta no resultado.

    Tasks com status=done sao ignoradas, portanto o caminho PERMANENT de
    `compute_sector` nunca e alcancado por esta funcao.

    Returns:
        Lista de (dependent_task_id, new_sector, new_color).
        Vazia se nenhuma task tem changed_task_id em suas deps.
    """
    result: list[tuple[str, Sector, str]] = []
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
    "PERMANENT_ACCENT",
    "compute_sector",
    "compute_sector_change_propagation",
    "count_open_deps",
    "has_open_deps_for",
]
