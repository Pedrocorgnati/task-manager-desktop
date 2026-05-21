# suite: contract | module: module-2-setores-dependencias | task: TASK-3
# @tdd-unlocked: 2026-05-21 (hardening round repo layer; ver source.md 05-20)
#   Justificativa: o hardening round (fix #3) tornou update_order_indexes
#   RENORMALIZADORA — apos aplicar os pares, os order_index de todas as tasks
#   ativas sao reescritos para uma sequencia contigua 0..N-1 na ordem canonica
#   (favorito DESC, order_index ASC, id ASC), eliminando buracos/colisoes. O
#   contrato de ORDEM relativa nao muda; apenas os valores literais ficam
#   densos. test_update_order_indexes_persists_in_single_transaction passa a
#   verificar a ordem relativa + contiguidade em vez dos literais de entrada.
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
    """update_order_indexes aplica os UPDATE numa transacao e RENORMALIZA.

    Given uma lista [(task_id, order_index), ...] com 3 tasks no repo
    When update_order_indexes(pairs) e chamado
    Then a ORDEM relativa pedida pelos pares e persistida
    And os order_index resultantes formam uma sequencia contigua 0..N-1
        (hardening fix #3: sem buracos nem colisoes)
    And a operacao acontece dentro de uma unica transacao.
    """
    from task_manager_desktop.core.models import Task

    repo = repo_factory
    for tid, oi in [("t1", 10), ("t2", 20), ("t3", 30)]:
        repo.create(Task(id=tid, title=tid, order_index=oi))

    # Pares pedem a ordem relativa t2 < t3 < t1.
    repo.update_order_indexes([("t1", 3), ("t2", 1), ("t3", 2)])

    rows = {
        r["id"]: r["order_index"]
        for r in repo._conn.execute("SELECT id, order_index FROM tasks")
    }
    # Renormalizacao: sequencia contigua 0..N-1 (sem buracos).
    assert sorted(rows.values()) == [0, 1, 2]
    # Ordem relativa pedida e preservada: t2 < t3 < t1.
    assert rows["t2"] < rows["t3"] < rows["t1"]


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
