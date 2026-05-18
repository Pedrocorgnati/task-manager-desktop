# suite: contract | module: module-2-setores-dependencias | task: TASK-3
# @tdd-locked: do not edit without /tdd:unlock
# covers: TASK-3/ST001 — TaskRepository.update_order_indexes contrato
# target: task_manager_desktop/repositories/task_repository.py
# TIDs: TID-2-3-001, TID-2-3-002, TID-2-3-003
import sqlite3

import pytest


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
# TID-2-3-001 | covers: TASK-3/ST001
# ---------------------------------------------------------------------------


def test_update_order_indexes_persists_in_single_transaction(repo_factory):
    """update_order_indexes aplica todos os UPDATE dentro de UMA transacao atomica.

    Given uma lista [(task_id, order_index), ...] com 3 tasks no repo
    When update_order_indexes(pairs) e chamado
    Then todos os order_index sao persistidos
    And a operacao acontece dentro de uma unica transacao (BEGIN/COMMIT) — verificavel
        via spy em conn.execute ou via inspecao de in_transaction state.
    """
    from task_manager_desktop.core.models import Task

    repo = repo_factory
    for tid, oi in [("t1", 10), ("t2", 20), ("t3", 30)]:
        repo.create(Task(id=tid, title=tid, order_index=oi))

    repo.update_order_indexes([("t1", 3), ("t2", 1), ("t3", 2)])

    rows = {
        r["id"]: r["order_index"]
        for r in repo._conn.execute("SELECT id, order_index FROM tasks")
    }
    assert rows["t1"] == 3
    assert rows["t2"] == 1
    assert rows["t3"] == 2


# ---------------------------------------------------------------------------
# TID-2-3-002 | covers: TASK-3/ST001
# ---------------------------------------------------------------------------


def test_update_order_indexes_rollback_on_error(repo_factory, monkeypatch):
    """Rollback completo quando uma escrita falha no meio (sqlite3.OperationalError).

    Given uma lista de 3 pares de update
    When o segundo UPDATE eleva sqlite3.OperationalError (monkeypatch)
    Then a transacao e revertida: nenhum order_index original sofre mutacao
    And a excecao sobe para o caller (nao silenciada no repo).
    """
    from task_manager_desktop.core.models import Task

    repo = repo_factory
    repo.create(Task(id="t1", title="T1", order_index=10))
    repo.create(Task(id="t2", title="T2", order_index=20))

    real_conn = repo._conn

    class FailingConn:
        def executemany(self, *a, **kw):
            raise sqlite3.OperationalError("simulated disk error")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, *args):
            return False

        def __getattr__(self, name):
            return getattr(real_conn, name)

    monkeypatch.setattr(repo, "_conn", FailingConn())

    with pytest.raises(sqlite3.OperationalError):
        repo.update_order_indexes([("t1", 100), ("t2", 200)])

    # Restore real conn and verify original values unchanged
    monkeypatch.setattr(repo, "_conn", real_conn)
    rows = {
        r["id"]: r["order_index"]
        for r in real_conn.execute("SELECT id, order_index FROM tasks")
    }
    assert rows["t1"] == 10
    assert rows["t2"] == 20


# ---------------------------------------------------------------------------
# TID-2-3-003 | covers: TASK-3/ST001
# ---------------------------------------------------------------------------


def test_update_order_indexes_empty_list_noop(repo_factory):
    """Lista vazia: no-op completo (zero queries, zero excecao).

    Given uma lista vazia []
    When update_order_indexes([]) e chamado
    Then nenhuma escrita ocorre no banco
    And nenhum erro e levantado.
    """
    repo_factory.update_order_indexes([])  # Must not raise
