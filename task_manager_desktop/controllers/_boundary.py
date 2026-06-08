"""Helpers de boundary compartilhados por CreateTaskController e EditTaskController.

Centraliza, num unico ponto, os tres contratos da secao 3.5 do source.md:

1. Coercao/validacao de range booleano para `favorito` e `permanente`
   (`coerce_flag`) — garante simetria estrita entre criacao e edicao.
2. Resolucao de `Status` na criacao/edicao (`resolve_status`) — default
   `PENDING` quando ausente, `ValueError` quando explicitamente invalido
   (nunca fallback silencioso).
3. Recomputo de setor pos-persistencia (`recompute_sector`) — o controller
   recalcula o setor via `compute_sector`; a UI nao recalcula por conta propria.

Valores invalidos levantam `ValueError` no boundary do controller, antes de
qualquer escrita no repositorio.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from task_manager_desktop.core.models import Sector, Status, Task
from task_manager_desktop.core.sector import compute_sector, has_open_deps_for

if TYPE_CHECKING:
    from task_manager_desktop.repositories.task_repository import TaskRepository

# Conjunto canonico de inteiros aceitos para um flag booleano no boundary.
# `True`/`False` sao tratados a parte (subclasse de int); aqui sobram 0 e 1 puros.
_VALID_FLAG_INTS: tuple[int, int] = (0, 1)


def coerce_flag(value: object, field_name: str) -> bool:
    """Coage `value` para `bool`, aceitando apenas `{True, False, 0, 1}`.

    Levanta `ValueError` para `None`, `str`, `float` ou `int` fora de `{0, 1}`,
    de modo que o erro apareca no boundary do controller, antes de qualquer
    escrita no repositorio (source.md secao 3.5). Nao coage silenciosamente.
    """
    if isinstance(value, bool):
        return value
    # `bool` ja foi tratado acima; aqui so chega `int` puro.
    if isinstance(value, int) and value in _VALID_FLAG_INTS:
        return bool(value)
    raise ValueError(
        f"{field_name} deve ser booleano (True, False, 0 ou 1); "
        f"recebido {value!r} do tipo {type(value).__name__}"
    )


def resolve_status(value: object, *, default: Status = Status.PENDING) -> Status:
    """Resolve `value` para um `Status` valido.

    - `None` (caller nao forneceu): retorna `default` (`PENDING` na criacao).
    - `Status`: retornado como esta.
    - `str`: convertido via `Status(value)`; valor invalido levanta `ValueError`.
    - qualquer outro tipo: levanta `ValueError`.

    Nunca faz fallback silencioso para `PENDING` quando um valor explicito e
    invalido (source.md secao 3.5).
    """
    if value is None:
        return default
    if isinstance(value, Status):
        return value
    if isinstance(value, str):
        try:
            return Status(value)
        except ValueError as exc:
            aceitos = ", ".join(s.value for s in Status)
            raise ValueError(
                f"status invalido: {value!r}; valores aceitos: {aceitos}"
            ) from exc
    raise ValueError(
        f"status deve ser str ou Status; recebido {value!r} "
        f"do tipo {type(value).__name__}"
    )


def recompute_sector(
    repo: TaskRepository,
    task_id: str,
) -> tuple[Task, tuple[Sector, str]] | tuple[None, None]:
    """Recarrega a task persistida e recomputa seu setor via `compute_sector`.

    Retorna `(task, (setor, cor))` para o controller devolver a UI; a UI consome
    o resultado em vez de recalcular o setor por conta propria (source.md secao
    3.5). Se a task nao existir mais (ex.: removida em corrida), retorna
    `(None, None)` para o caller decidir o que fazer sem mascarar o estado.
    """
    task = repo.get_by_id(task_id)
    if task is None:
        return None, None
    all_tasks = {t.id: t for t in repo.list_active()}
    open_deps = has_open_deps_for(task, all_tasks)
    sector = compute_sector(
        task.status, open_deps, task.permanente, task.em_preparacao
    )
    return task, sector


__all__ = ["coerce_flag", "recompute_sector", "resolve_status"]
