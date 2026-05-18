# suite: integration (perf) | module: module-2-setores-dependencias | task: TASK-2
# @tdd-locked: do not edit without /tdd:unlock
# covers: TASK-2/ST008, AC-T-005 — performance gate de compute_sector_change_propagation
# target: task_manager_desktop/core/sector.py:compute_sector_change_propagation
# TIDs: TID-2-2-019
#
# Suite logica = integration (perf). Diretorio benchmark/ por convencao do projeto.
import pytest

# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_factory(tmp_path):
    """Constroi TaskRepository em tmp_path/tm.db com schema canonico."""
    import sqlite3

    from task_manager_desktop.core.db import run_migrations
    from task_manager_desktop.repositories.task_repository import TaskRepository

    db_path = tmp_path / "tm.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    repo = TaskRepository(conn, db_path=str(db_path))
    yield repo
    conn.close()


# ---------------------------------------------------------------------------
# TID-2-2-019 | covers: TASK-2/ST008, AC-T-005
# ---------------------------------------------------------------------------


def test_propagation_p95_under_50ms_2000_tasks(repo_factory):
    """Performance gate: compute_sector_change_propagation p95 <= 50ms em 2000 tasks.

    Seed canonico (TEST-PLAN §6.2):
      - 2000 tasks total
      - 50% sem deps
      - 30% com 1 dep
      - 15% com 2-3 deps
      - 5% com 4-5 deps
      - pick task A com ~100 dependentes diretos para forcar carga real

    Asserts:
      - p95(tempos_amostrados) <= 50ms
      - p99 documentado em saida do teste (nao falha — observabilidade)
    """
    import time

    from task_manager_desktop.core.models import Status, Task
    from task_manager_desktop.core.sector import compute_sector_change_propagation

    # Build 2000 tasks in memory (no DB needed — function is pure)
    n = 2000
    anchor_id = "ANCHOR"

    tasks: dict[str, Task] = {}

    # Anchor task (done) — the one whose change we propagate
    tasks[anchor_id] = Task(id=anchor_id, title="Anchor", status=Status.DONE, deps=[], order_index=0)

    # ~100 direct dependents of ANCHOR
    anchor_deps_count = 100
    for i in range(anchor_deps_count):
        tid = f"dep_{i:04d}"
        tasks[tid] = Task(id=tid, title=f"Dep{i}", status=Status.PENDING, deps=[anchor_id], order_index=i + 1)

    # Fill remaining tasks with varied dep patterns
    remaining = n - 1 - anchor_deps_count
    other_ids = [f"t_{i:04d}" for i in range(remaining)]
    for idx, tid in enumerate(other_ids):
        order = anchor_deps_count + idx + 2
        bucket = idx % 100
        if bucket < 50:
            # 50%: no deps
            tasks[tid] = Task(id=tid, title=tid, status=Status.PENDING, deps=[], order_index=order)
        elif bucket < 80:
            # 30%: 1 dep (non-anchor)
            prev = other_ids[idx - 1] if idx > 0 else anchor_id
            tasks[tid] = Task(id=tid, title=tid, status=Status.PENDING, deps=[prev], order_index=order)
        elif bucket < 95:
            # 15%: 2-3 deps
            dep1 = other_ids[idx - 1] if idx > 0 else anchor_id
            dep2 = other_ids[idx - 2] if idx > 1 else anchor_id
            tasks[tid] = Task(id=tid, title=tid, status=Status.PENDING, deps=[dep1, dep2], order_index=order)
        else:
            # 5%: 4-5 deps
            d_ids = [other_ids[max(0, idx - k)] for k in range(1, 5)]
            tasks[tid] = Task(id=tid, title=tid, status=Status.PENDING, deps=d_ids, order_index=order)

    assert len(tasks) == n, f"expected {n} tasks, got {len(tasks)}"

    # Run 50 samples
    samples_ms: list[float] = []
    for _ in range(50):
        t0 = time.perf_counter()
        compute_sector_change_propagation(anchor_id, tasks)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        samples_ms.append(elapsed_ms)

    samples_ms.sort()
    p50 = samples_ms[24]
    p95 = samples_ms[47]
    p99 = samples_ms[49]

    print(f"\nbenchmark: n={n}, deps_on_anchor={anchor_deps_count}")
    print(f"  p50={p50:.2f}ms  p95={p95:.2f}ms  p99={p99:.2f}ms")

    # Save evidence JSON
    import json
    import os

    evidence_dir = "output/wbs/task-manager-desktop/modules/module-2-setores-dependencias/evidence/TASK-2"
    os.makedirs(evidence_dir, exist_ok=True)
    with open(os.path.join(evidence_dir, "benchmark.json"), "w") as fh:
        json.dump({"n": n, "anchor_deps": anchor_deps_count, "samples": 50, "p50_ms": round(p50, 3), "p95_ms": round(p95, 3), "p99_ms": round(p99, 3)}, fh, indent=2)

    assert p95 <= 50.0, f"p95={p95:.2f}ms excede budget de 50ms"
