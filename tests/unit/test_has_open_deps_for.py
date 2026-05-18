# suite: unit | module: module-2-setores-dependencias | task: TASK-2
# @tdd-locked: do not edit without /tdd:unlock
# covers: TASK-2/ST005 — has_open_deps_for (logica pura)
# target: task_manager_desktop/core/sector.py
# TIDs: TID-2-2-006, TID-2-2-008
from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------


@pytest.fixture
def tasks_dict():
    """Constroi dict[str, Task] simples para testar has_open_deps_for."""
    from task_manager_desktop.core.models import Status, Task

    done = Task(
        id="DONE",
        title="D",
        status=Status.DONE,
        deps=[],
        order_index=0,
        completed_at="2026-01-01T00:00:00Z",
    )
    pending = Task(id="PEND", title="P", status=Status.PENDING, deps=[], order_index=1)
    return {"DONE": done, "PEND": pending}


# ---------------------------------------------------------------------------
# TID-2-2-006 | covers: TASK-2/ST005, US-001#cenario-4, AC-T-003
# ---------------------------------------------------------------------------


def test_invalid_dep_ids_are_ignored(tasks_dict):
    """has_open_deps_for: dep_ids que nao existem no all_tasks dict sao silenciosamente ignorados.

    Task com deps=["GHOST"] onde "GHOST" nao existe em all_tasks
    deve retornar False (sem KeyError).
    """
    from task_manager_desktop.core.models import Task
    from task_manager_desktop.core.sector import has_open_deps_for

    ghost_task = Task(id="GHOST_OWNER", title="G", deps=["GHOST"], order_index=2)
    result = has_open_deps_for(ghost_task, tasks_dict)
    assert result is False


# ---------------------------------------------------------------------------
# TID-2-2-008 | covers: TASK-2/ST005
# ---------------------------------------------------------------------------


def test_done_dep_does_not_block(tasks_dict):
    """has_open_deps_for: dep com status='done' nao conta como bloqueio — retorna False."""
    from task_manager_desktop.core.models import Task
    from task_manager_desktop.core.sector import has_open_deps_for

    # DONE is in tasks_dict with status=DONE
    task_with_done_dep = Task(id="CONSUMER", title="C", deps=["DONE"], order_index=2)
    result = has_open_deps_for(task_with_done_dep, tasks_dict)
    assert result is False
