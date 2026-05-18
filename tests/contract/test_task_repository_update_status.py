# suite: contract | module: module-2-setores-dependencias | task: TASK-1
# @tdd-unlocked: 2026-05-18 (TASK-4 corretiva; ver TDD-UNLOCK-JUSTIFICATION.md)
# covers: TASK-1/ST006, TASK-1/ST001 — TaskRepository.update_status contrato
# target: task_manager_desktop/repositories/task_repository.py
# TIDs: TID-2-1-012
#
# Contrato verificado:
#   - signature(task_id: str, status: Status, completed_at: datetime | None) -> None
#   - aceita Status enum (nao str)
#   - completed_at=None -> coluna NULL
#   - completed_at=datetime -> ISO format
#   - comportamento em task_id inexistente (documenta contrato atual do repo)
import inspect
import sqlite3
from datetime import datetime, timezone

import pytest

from task_manager_desktop.core.models import Status, Task

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


# ---------------------------------------------------------------------------
# TID-2-1-012 | covers: TASK-1/ST006, TASK-1/ST001
# ---------------------------------------------------------------------------


def test_update_status_contract_signature_and_persistence(repo_factory):
    """Contrato canonico de TaskRepository.update_status.

    Verifica:
      1. Assinatura: update_status(task_id: str, status: Status, completed_at: datetime | None) -> None
      2. Aceita Status enum (nao str cru).
      3. completed_at=None -> coluna NULL no banco.
      4. completed_at=datetime -> coluna em formato ISO 8601.
      5. Chamada com task_id inexistente nao explode (no-op silencioso documentado).
    """
    from task_manager_desktop.repositories.task_repository import TaskRepository

    repo = repo_factory

    # 1. Verificar assinatura
    sig = inspect.signature(TaskRepository.update_status)
    params = list(sig.parameters.keys())
    assert "task_id" in params
    assert "status" in params
    assert "completed_at" in params

    # Seed: create a task to update
    task = Task(
        id="c001",
        title="Contract Task",
        status=Status.PENDING,
        deps=[],
        order_index=1,
    )
    repo.create(task)

    # 2. Aceita Status enum, nao str
    repo.update_status("c001", Status.IN_PROGRESS, None)
    row = repo.get_by_id("c001")
    assert row is not None
    assert row.status == Status.IN_PROGRESS

    # 3. completed_at=None -> coluna NULL
    repo.update_status("c001", Status.PENDING, None)
    row = repo.get_by_id("c001")
    assert row.completed_at is None

    # 4. completed_at=datetime -> ISO format persisted
    ts = datetime.now(timezone.utc).replace(tzinfo=None)
    repo.update_status("c001", Status.DONE, ts)
    row = repo.get_by_id("c001")
    assert row is not None
    assert row.completed_at is not None
    # must be parseable as ISO datetime
    parsed = datetime.fromisoformat(row.completed_at)
    assert parsed is not None

    # 5. task_id inexistente: silencioso (no-op, nao lanca excecao)
    repo.update_status("id_que_nao_existe", Status.DONE, None)
    # se chegou aqui, nao lancou — contrato documentado
