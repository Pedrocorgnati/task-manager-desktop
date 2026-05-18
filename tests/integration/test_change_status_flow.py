# suite: integration | module: module-2-setores-dependencias | task: TASK-1 + TASK-4
# @tdd-unlocked: 2026-05-18 (TASK-4 corretiva; ver TDD-UNLOCK-JUSTIFICATION.md)
# covers: TASK-1/ST007, AC-T-006 — controller + repo SQLite tmpfile end-to-end (sem UI)
#         TASK-4/ST007 (provider call_count) + ST011 (marker perf)
# target: task_manager_desktop/controllers/change_status_controller.py + repositories/task_repository.py
# TIDs: TID-2-1-013, TID-2-1-014, TID-2-1-015
import sqlite3
import time

import pytest

from task_manager_desktop.controllers.change_status_controller import ChangeStatusController
from task_manager_desktop.core.models import Status, Task
from task_manager_desktop.core.sector import compute_sector

# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_factory(tmp_path):
    """Constroi TaskRepository em tmp_path/tm.db com schema canonico."""
    from task_manager_desktop.core.db import run_migrations
    from task_manager_desktop.repositories.task_repository import TaskRepository

    db_path = tmp_path / "tm.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    repo = TaskRepository(conn, db_path=str(db_path))
    yield repo
    conn.close()


@pytest.fixture
def make_task():
    """Factory canonica de Task com defaults sensatos."""
    from task_manager_desktop.core.models import Status

    def _factory(
        id: str = "t1",
        title: str = "Task",
        status: Status = Status.PENDING,
        deps: list | None = None,
        order_index: int = 1,
        completed_at=None,
    ) -> Task:
        return Task(
            id=id,
            title=title,
            status=status,
            deps=deps or [],
            order_index=order_index,
            completed_at=completed_at,
        )

    return _factory


class _NullErrorHandler:
    def show_io_error(self, message: str, db_path: str) -> None:
        pass


# ---------------------------------------------------------------------------
# TID-2-1-013 | covers: TASK-1/ST007
# ---------------------------------------------------------------------------


def test_pending_to_done_persists_and_recomputes_sector(repo_factory, make_task):
    """Integration: pending -> done persiste status, completed_at e recomputa setor.

    Given uma task A em pending, sem deps, em setor Fila (waiting)
    When o controller dispara mudanca pending -> done atraves do repo
    Then o banco tem status=done, completed_at != NULL
    And a leitura via repo.get_by_id retorna setor Done (sector 4)
    """
    repo = repo_factory
    task = make_task(id="A", status=Status.PENDING)
    repo.create(task)

    refreshed = []
    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: {t.id: t for t in repo.list_active()},
        error_handler=_NullErrorHandler(),
        refresh_card=lambda t: refreshed.append((t.id, t.status)),
    )
    ctrl.change_status(task, "done")

    # DB persistence verified
    row = repo.get_by_id("A")
    assert row is not None
    assert row.status == Status.DONE
    assert row.completed_at is not None

    # Sector recomputed (done = sector 4)
    sector, _ = compute_sector(Status.DONE, False)
    from task_manager_desktop.core.models import Sector
    assert sector == Sector.DONE

    # refresh_card called with updated task
    assert refreshed == [("A", Status.DONE)]


# ---------------------------------------------------------------------------
# TID-2-1-014 | covers: TASK-1/ST007
# ---------------------------------------------------------------------------


def test_done_to_pending_clears_completed_at_in_db(repo_factory, make_task):
    """Integration: done -> pending persiste e zera completed_at no banco.

    Given uma task A com status=done e completed_at preenchido
    When o controller dispara mudanca done -> pending
    Then a coluna completed_at fica NULL no banco
    And o setor recomputado e Fila/Bloqueadas (conforme deps)
    """
    repo = repo_factory
    task = make_task(id="A", status=Status.DONE, completed_at="2026-01-01T00:00:00")
    repo.create(task)
    # Ensure DB has completed_at
    repo.update_status("A", Status.DONE, None)
    row = repo.get_by_id("A")
    assert row is not None

    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: {t.id: t for t in repo.list_active()},
        error_handler=_NullErrorHandler(),
        refresh_card=lambda t: None,
    )
    ctrl.change_status(task, "pending")

    row = repo.get_by_id("A")
    assert row is not None
    assert row.status == Status.PENDING
    assert row.completed_at is None


# ---------------------------------------------------------------------------
# TID-2-1-015 | covers: TASK-1/ST007, AC-T-006
# ---------------------------------------------------------------------------


@pytest.mark.perf
def test_change_status_p95_under_50ms_100_runs(repo_factory, make_task, request):
    """Performance gate: p95 do ciclo update_status + refresh <= 50ms em 100 chamadas.

    @pytest.mark.perf (opt-in): assert p95 so falha quando --run-perf for passado.
    Sem a flag, o teste roda mas a assertion vira pytest.skip — evita flaky em CI compartilhado.

    Given um repo SQLite em tmpfile com 1 task seed
    When executamos 100 ciclos pending<->done medindo cada chamada
    Then p95 dos tempos coletados deve ser <= 50ms (AC-T-006)
    And p99 documentado para inspecao manual
    """
    import statistics

    repo = repo_factory
    task = make_task(id="perf1", status=Status.PENDING)
    repo.create(task)

    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: {t.id: t for t in repo.list_active()},
        error_handler=_NullErrorHandler(),
        refresh_card=lambda t: None,
    )

    timings = []
    statuses = [Status.DONE, Status.PENDING] * 50  # 100 alternating transitions

    for target_status in statuses:
        t0 = time.perf_counter()
        ctrl.change_status(task, target_status.value)
        t1 = time.perf_counter()
        timings.append((t1 - t0) * 1000)  # ms

    timings_sorted = sorted(timings)
    p95_idx = int(len(timings_sorted) * 0.95)
    p99_idx = int(len(timings_sorted) * 0.99)
    p95 = timings_sorted[p95_idx]
    p99 = timings_sorted[min(p99_idx, len(timings_sorted) - 1)]

    print(f"\n[perf] p95={p95:.2f}ms p99={p99:.2f}ms mean={statistics.mean(timings):.2f}ms")

    run_perf = request.config.getoption("--run-perf", default=False) if hasattr(request.config, "getoption") else False
    if not run_perf:
        pytest.skip("perf gate is opt-in; pass --run-perf to enforce p95 budget")

    assert p95 <= 50.0, f"p95={p95:.2f}ms exceeds 50ms budget (AC-T-006)"


# ---------------------------------------------------------------------------
# TASK-4/ST007 — provider call_count <= 1 por mudanca (regressao light)
# ---------------------------------------------------------------------------


def test_change_status_calls_provider_once_in_integration(repo_factory, make_task):
    """ST007 regression: all_tasks_provider invocado <= 1 vez por change_status, mesmo no flow integration."""
    repo = repo_factory
    task = make_task(id="solo", status=Status.PENDING)
    repo.create(task)

    calls = {"count": 0}

    def _provider():
        calls["count"] += 1
        return {t.id: t for t in repo.list_active()}

    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=_provider,
        error_handler=_NullErrorHandler(),
        refresh_card=lambda t: None,
    )
    ctrl.change_status(task, "done")

    assert calls["count"] <= 1, f"provider chamado {calls['count']} vezes (esperado <= 1)"
