from __future__ import annotations

from collections.abc import Iterable

from task_manager_desktop.core.models import TaskType

ALL_TASK_TYPES: frozenset[str] = frozenset(t.value for t in TaskType)


def _normalize_type_filter(task_types: Iterable[str | TaskType] | None) -> frozenset[str]:
    if task_types is None:
        return ALL_TASK_TYPES
    return frozenset(
        item.value if isinstance(item, TaskType) else str(item)
        for item in task_types
    )


def is_active(
    task_types: Iterable[str | TaskType] | None = None,
) -> bool:
    """O filtro de tipo so esta ativo quando NEM todos os tipos estao marcados.

    Regra de produto: com os 3 checkboxes marcados (== ALL_TASK_TYPES) o filtro
    e inativo e todos os cards/subtasks renderizam. Basta desmarcar um para o
    filtro passar a valer.
    """
    if _normalize_type_filter(task_types) != ALL_TASK_TYPES:
        return True
    return False


def card_matches_subtasks(
    subtask_types: Iterable[str | TaskType],
    task_types: Iterable[str | TaskType] | None = None,
) -> bool:
    """Visibilidade de um card principal SOB filtro de tipo ativo.

    O tipo (agent/dev/human) deixou de viver na task e passou a viver nas suas
    subtasks. Com o filtro ATIVO (nem todos os tipos marcados), um card so
    renderiza se possuir ao menos uma subtask cujo tipo esta no conjunto
    selecionado. Cards sem subtasks (ou sem subtasks do tipo marcado) somem.

    Quando o filtro esta inativo (todos os tipos), a visibilidade do card NAO
    depende das subtasks — quem decide e o caller (ver is_active). Esta funcao
    so deve ser consultada quando is_active() retorna True.
    """
    selected = _normalize_type_filter(task_types)
    have = frozenset(
        item.value if isinstance(item, TaskType) else str(item)
        for item in subtask_types
    )
    return bool(have & selected)


__all__ = ["ALL_TASK_TYPES", "card_matches_subtasks", "is_active"]
