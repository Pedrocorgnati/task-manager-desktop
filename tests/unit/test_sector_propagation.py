# suite: unit | module: module-2-setores-dependencias | task: TASK-2
# @tdd-locked: do not edit without /tdd:unlock
# covers: TASK-2/ST005 — compute_sector_change_propagation (logica pura)
# target: task_manager_desktop/core/sector.py
# TIDs: TID-2-2-001, TID-2-2-002, TID-2-2-003, TID-2-2-004,
#        TID-2-2-005, TID-2-2-007, TID-2-2-009
from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------


@pytest.fixture
def all_tasks_dict():
    """Constroi dict[str, Task] canonico com seeds para propagacao."""
    from task_manager_desktop.core.models import Status, Task

    def _build(specs: list[tuple[str, str, list[str]]]) -> dict:
        """specs: [(id, status, deps), ...]"""
        result = {}
        for tid, status_str, deps in specs:
            result[tid] = Task(
                id=tid,
                title=tid,
                status=Status(status_str),
                deps=deps,
                order_index=1,
            )
        return result

    return _build


# ---------------------------------------------------------------------------
# TID-2-2-001 | covers: TASK-2/ST005, US-005#cenario-1
# ---------------------------------------------------------------------------


def test_two_dependents_promoted_on_dep_done(all_tasks_dict):
    """compute_sector_change_propagation: dois dependentes de A sao promovidos quando A vai a done."""
    from task_manager_desktop.core.models import Sector
    from task_manager_desktop.core.sector import compute_sector_change_propagation

    tasks = all_tasks_dict([
        ("A", "done", []),
        ("B", "pending", ["A"]),
        ("C", "pending", ["A"]),
    ])
    result = compute_sector_change_propagation("A", tasks)
    ids = {r[0] for r in result}
    sectors = {r[0]: r[1] for r in result}
    assert "B" in ids
    assert "C" in ids
    assert "A" not in ids
    assert sectors["B"] == Sector.WAITING
    assert sectors["C"] == Sector.WAITING


# ---------------------------------------------------------------------------
# TID-2-2-002 | covers: TASK-2/ST005, US-005#cenario-2
# ---------------------------------------------------------------------------


def test_dependent_with_other_open_dep_stays_blocked(all_tasks_dict):
    """compute_sector_change_propagation: dependente com outra dep aberta permanece bloqueado."""
    from task_manager_desktop.core.models import Sector
    from task_manager_desktop.core.sector import compute_sector_change_propagation

    # A done, E still pending — D depends on both A and E
    tasks = all_tasks_dict([
        ("A", "done", []),
        ("E", "pending", []),
        ("D", "pending", ["A", "E"]),
    ])
    result = compute_sector_change_propagation("A", tasks)
    sectors = {r[0]: r[1] for r in result}
    # D has E still open, so it stays BLOCKED
    assert sectors.get("D") == Sector.BLOCKED


# ---------------------------------------------------------------------------
# TID-2-2-003 | covers: TASK-2/ST005, US-005#cenario-3
# ---------------------------------------------------------------------------


def test_reverting_done_reblocks_dependents(all_tasks_dict):
    """compute_sector_change_propagation: reverter done re-bloqueia os dependentes."""
    from task_manager_desktop.core.models import Sector
    from task_manager_desktop.core.sector import compute_sector_change_propagation

    # A is now pending again — F which depended on A is re-blocked
    tasks = all_tasks_dict([
        ("A", "pending", []),
        ("F", "pending", ["A"]),
    ])
    result = compute_sector_change_propagation("A", tasks)
    sectors = {r[0]: r[1] for r in result}
    assert sectors.get("F") == Sector.BLOCKED


# ---------------------------------------------------------------------------
# TID-2-2-004 | covers: TASK-2/ST005, US-005#cenario-4, AC-T-002, D-006
#              | bdd_scenario: Chain propagation is one level only (invariante negativa)
# ---------------------------------------------------------------------------


def test_chain_propagation_is_one_level_only(all_tasks_dict):
    """compute_sector_change_propagation: propagacao cobre apenas um nivel — D-006 (sem recursao).

    C->done: B (dep=[C]) promovido; A (dep=[B]) nao deve ser promovido nessa chamada.
    """
    from task_manager_desktop.core.models import Sector
    from task_manager_desktop.core.sector import compute_sector_change_propagation

    tasks = all_tasks_dict([
        ("C", "done", []),
        ("B", "pending", ["C"]),
        ("A", "pending", ["B"]),
    ])
    result = compute_sector_change_propagation("C", tasks)
    ids = {r[0] for r in result}
    sectors = {r[0]: r[1] for r in result}
    # B is a direct dependent of C → promoted to WAITING
    assert "B" in ids
    assert sectors["B"] == Sector.WAITING
    # A depends on B (not C) → NOT in result (one level only)
    assert "A" not in ids


# ---------------------------------------------------------------------------
# TID-2-2-005 | covers: TASK-2/ST005
# ---------------------------------------------------------------------------


def test_no_dependents_returns_empty(all_tasks_dict):
    """compute_sector_change_propagation: task sem dependentes retorna lista/dict vazio."""
    from task_manager_desktop.core.sector import compute_sector_change_propagation

    tasks = all_tasks_dict([
        ("Z", "done", []),
        ("X", "pending", []),  # no deps, not a dependent of Z
    ])
    result = compute_sector_change_propagation("Z", tasks)
    assert result == []


# ---------------------------------------------------------------------------
# TID-2-2-007 | covers: TASK-2/ST005
# ---------------------------------------------------------------------------


def test_self_excluded_from_result(all_tasks_dict):
    """compute_sector_change_propagation: a propria task alterada nao aparece no resultado."""
    from task_manager_desktop.core.sector import compute_sector_change_propagation

    tasks = all_tasks_dict([
        ("A", "done", []),
        ("B", "pending", ["A"]),
    ])
    result = compute_sector_change_propagation("A", tasks)
    ids = {r[0] for r in result}
    assert "A" not in ids


# ---------------------------------------------------------------------------
# TID-2-2-009 | covers: TASK-2/ST005, AC-T-004
# ---------------------------------------------------------------------------


def test_function_is_pure_no_mutation(all_tasks_dict):
    """compute_sector_change_propagation: e funcao pura — nao muta o dict de entrada."""
    from task_manager_desktop.core.sector import compute_sector_change_propagation

    tasks = all_tasks_dict([
        ("A", "done", []),
        ("B", "pending", ["A"]),
    ])
    # Capture state before
    b_status_before = tasks["B"].status
    b_deps_before = list(tasks["B"].deps)
    keys_before = set(tasks.keys())

    compute_sector_change_propagation("A", tasks)

    # State must be unchanged
    assert tasks["B"].status == b_status_before
    assert tasks["B"].deps == b_deps_before
    assert set(tasks.keys()) == keys_before


# ---------------------------------------------------------------------------
# Coverage gap — sector.py line 58 (DONE dependent skipped)
# ---------------------------------------------------------------------------


def test_done_dependent_excluded_from_propagation(all_tasks_dict):
    """compute_sector_change_propagation: dependente com status=done e ignorado."""
    from task_manager_desktop.core.sector import compute_sector_change_propagation

    tasks = all_tasks_dict([
        ("A", "done", []),
        ("B", "done", ["A"]),  # DONE dependent — must be excluded
    ])
    result = compute_sector_change_propagation("A", tasks)
    ids = {r[0] for r in result}
    assert "B" not in ids


# ---------------------------------------------------------------------------
# Coverage gap — sector.py line 10 (IN_PROGRESS sem deps abertas -> GREEN)
# ---------------------------------------------------------------------------


def test_in_progress_dependent_no_open_deps_gets_active(all_tasks_dict):
    """compute_sector_change_propagation: dependente in_progress sem deps abertas -> ACTIVE."""
    from task_manager_desktop.core.models import Sector
    from task_manager_desktop.core.sector import compute_sector_change_propagation

    tasks = all_tasks_dict([
        ("A", "done", []),
        ("B", "in_progress", ["A"]),  # IN_PROGRESS, only dep is now done
    ])
    result = compute_sector_change_propagation("A", tasks)
    sectors = {r[0]: r[1] for r in result}
    assert sectors.get("B") == Sector.ACTIVE
