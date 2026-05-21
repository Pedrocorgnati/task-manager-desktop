"""Testes do hardening round do TaskRepository (05-21).

Cobre os seis fixes da auditoria adversarial Codex aplicados em
task_manager_desktop/repositories/task_repository.py:

  1. rowcount enforcement em update()/update_status() (HARD)
  2. resiliencia a corrupcao em _row_to_task -> DataCorruptionError (SOFT)
  3. validacao de order_index + renormalizacao contigua (SOFT)
  4. hide_all_done() retorna HideAllDoneResult observavel (HARD)
  5. touch incondicional de updated_at em update_favorito/update_permanente/update (SOFT)
  6. update_subtask_text(subtask_id, text) -> None com contrato de linha unica (SOFT)
"""

from __future__ import annotations

import sqlite3

import pytest

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.exceptions import TaskNotFoundError
from task_manager_desktop.core.models import Status, Subtask, Task
from task_manager_desktop.repositories.task_repository import (
    DataCorruptionError,
    HideAllDoneResult,
    SubtaskNotFoundError,
    TaskRepository,
    _row_to_task,
)

# Colunas de uma linha de `tasks` na ordem que _row_to_task espera ler.
_TASK_ROW_COLS = (
    "id",
    "title",
    "status",
    "type",
    "deps",
    "notes",
    "order_index",
    "created_at",
    "completed_at",
    "hidden_at",
    "favorito",
    "permanente",
    "updated_at",
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    run_migrations(c)
    yield c
    c.close()


@pytest.fixture
def repo(conn):
    return TaskRepository(conn, db_path=":memory:")


def _task(id: str = "t1", title: str = "Test", **kw) -> Task:
    return Task(id=id, title=title, **kw)


# ── fix #1: rowcount enforcement em update() / update_status() ────────────────


def test_update_raises_task_not_found_on_unknown_id(repo):
    """update() generico em id inexistente levanta TaskNotFoundError (rowcount 0)."""
    with pytest.raises(TaskNotFoundError):
        repo.update("ghost", title="novo titulo")


def test_update_status_raises_task_not_found_on_unknown_id(repo):
    """update_status() em id inexistente levanta TaskNotFoundError (rowcount 0)."""
    with pytest.raises(TaskNotFoundError):
        repo.update_status("ghost", Status.DONE, None)


def test_update_succeeds_on_existing_task(repo):
    """update() em task existente nao levanta e persiste o campo."""
    repo.create(_task(id="a", title="antigo"))
    repo.update("a", title="novo")
    assert repo.get_by_id("a").title == "novo"


def test_update_status_succeeds_on_existing_task(repo):
    repo.create(_task(id="a", title="T", status=Status.PENDING))
    repo.update_status("a", Status.IN_PROGRESS, None)
    assert repo.get_by_id("a").status is Status.IN_PROGRESS


def test_update_empty_fields_is_noop_without_raising(repo):
    """update() sem campos validos retorna sem tocar o banco nem levantar."""
    repo.create(_task(id="a", title="T"))
    repo.update("a")  # nenhum campo -> early return, sem UPDATE
    assert repo.get_by_id("a").title == "T"


def test_enforce_single_row_raises_integrity_error_on_multiple_rows():
    """rowcount > 1 num UPDATE por id viola unicidade da PK -> IntegrityError.

    A PK de `tasks` torna impossivel inserir um id duplicado via repo, entao o
    guard de rowcount>1 e exercitado diretamente sobre _enforce_single_row.
    """
    from task_manager_desktop.repositories.task_repository import _enforce_single_row

    with pytest.raises(sqlite3.IntegrityError):
        _enforce_single_row(2, "dup", "update")


def test_enforce_single_row_raises_task_not_found_on_zero():
    from task_manager_desktop.repositories.task_repository import _enforce_single_row

    with pytest.raises(TaskNotFoundError):
        _enforce_single_row(0, "ghost", "update")


def test_enforce_single_row_passes_on_exactly_one():
    from task_manager_desktop.repositories.task_repository import _enforce_single_row

    _enforce_single_row(1, "ok", "update")  # nao levanta


# ── fix #2: _row_to_task fail-fast em corrupcao -> DataCorruptionError ─────────
#
# O schema canonico de `tasks` tem CHECK/NOT NULL em status/type/favorito/
# permanente, entao valores corrompidos nao entram via INSERT/UPDATE normal.
# A resiliencia de _row_to_task defende contra schema drift, edicao direta do
# arquivo .db ou migracao futura. Para exercer o caminho de corrupcao, os
# testes constroem uma linha sintetica numa tabela scratch SEM constraints.


@pytest.fixture
def fake_row(conn):
    """Fabrica de sqlite3.Row no formato de `tasks`, sem CHECK/NOT NULL.

    Retorna uma funcao que recebe overrides de coluna e devolve um sqlite3.Row
    com o mesmo schema posicional que _row_to_task consome.
    """
    conn.execute(
        "CREATE TABLE _scratch_tasks ("
        + ", ".join(f"{c}" for c in _TASK_ROW_COLS)
        + ")"
    )
    defaults = {
        "id": "a",
        "title": "T",
        "status": "pending",
        "type": "agent",
        "deps": "",
        "notes": "",
        "order_index": 0,
        "created_at": "2026-01-01",
        "completed_at": None,
        "hidden_at": None,
        "favorito": 0,
        "permanente": 0,
        "updated_at": None,
    }

    def _make(**overrides):
        values = {**defaults, **overrides}
        placeholders = ", ".join("?" for _ in _TASK_ROW_COLS)
        conn.execute("DELETE FROM _scratch_tasks")
        conn.execute(
            f"INSERT INTO _scratch_tasks VALUES ({placeholders})",
            tuple(values[c] for c in _TASK_ROW_COLS),
        )
        return conn.execute("SELECT * FROM _scratch_tasks").fetchone()

    return _make


def test_row_to_task_raises_on_corrupt_status(fake_row):
    """Status fora do dominio na linha -> DataCorruptionError nomeando id/coluna."""
    with pytest.raises(DataCorruptionError) as exc:
        _row_to_task(fake_row(id="a", status="banana"))
    assert "status" in str(exc.value)
    assert "a" in str(exc.value)


def test_row_to_task_raises_on_corrupt_type(fake_row):
    with pytest.raises(DataCorruptionError) as exc:
        _row_to_task(fake_row(type="wizard"))
    assert "type" in str(exc.value)


def test_row_to_task_raises_on_corrupt_favorito(fake_row):
    with pytest.raises(DataCorruptionError) as exc:
        _row_to_task(fake_row(favorito=7))
    assert "favorito" in str(exc.value)


def test_row_to_task_raises_on_corrupt_permanente(fake_row):
    with pytest.raises(DataCorruptionError) as exc:
        _row_to_task(fake_row(permanente="yes"))
    assert "permanente" in str(exc.value)


def test_row_to_task_raises_on_null_status(fake_row):
    with pytest.raises(DataCorruptionError):
        _row_to_task(fake_row(status=None))


def test_row_to_task_tolerates_whitespace_and_case(fake_row):
    """Variacao tolerada (espacos / caixa) e coagida ao valor canonico."""
    task = _row_to_task(fake_row(status="  DONE  ", type="Agent"))
    assert task.status is Status.DONE
    assert task.type.value == "agent"


def test_row_to_task_null_favorito_defaults_false(fake_row):
    """favorito/permanente NULL (linha pre-v7) e tratado como False."""
    task = _row_to_task(fake_row(favorito=None, permanente=None))
    assert task.favorito is False
    assert task.permanente is False


def test_row_to_task_accepts_canonical_values(fake_row):
    """Sanidade: uma linha integra nao levanta e mapeia corretamente."""
    task = _row_to_task(fake_row(status="done", type="dev", favorito=1, permanente=1))
    assert task.status is Status.DONE
    assert task.favorito is True
    assert task.permanente is True


# ── fix #3: validacao de order_index + renormalizacao ─────────────────────────


@pytest.mark.parametrize("bad", [-1, -10, True, False, "0", 1.5, None])
def test_create_rejects_invalid_order_index(repo, bad):
    with pytest.raises(ValueError):
        repo.create(_task(id="a", title="T", order_index=bad))


def test_update_rejects_negative_order_index(repo):
    repo.create(_task(id="a", title="T"))
    with pytest.raises(ValueError):
        repo.update("a", order_index=-3)


def test_update_order_indexes_rejects_negative(repo):
    repo.create(_task(id="a", title="T"))
    with pytest.raises(ValueError):
        repo.update_order_indexes([("a", -1)])


def test_update_order_indexes_renormalizes_to_contiguous(repo, conn):
    """Apos reorder, order_index das tasks ativas vira sequencia contigua 0..N-1."""
    repo.create(_task(id="a", title="A", order_index=0))
    repo.create(_task(id="b", title="B", order_index=1))
    repo.create(_task(id="c", title="C", order_index=2))
    # Aplica indices esparsos (buracos): 10, 20, 30.
    repo.update_order_indexes([("a", 10), ("b", 20), ("c", 30)])
    rows = conn.execute(
        "SELECT id, order_index FROM tasks WHERE hidden_at IS NULL "
        "ORDER BY order_index ASC"
    ).fetchall()
    indices = [r["order_index"] for r in rows]
    assert indices == [0, 1, 2]


def test_update_order_indexes_preserves_favorito_sort_contract(repo, conn):
    """Renormalizacao respeita (favorito DESC, order_index ASC, id ASC)."""
    repo.create(_task(id="a", title="A", order_index=0))
    repo.create(_task(id="b", title="B", order_index=1, favorito=True))
    repo.create(_task(id="c", title="C", order_index=2))
    repo.update_order_indexes([("a", 5), ("b", 6), ("c", 7)])
    rows = conn.execute(
        "SELECT id FROM tasks WHERE hidden_at IS NULL "
        "ORDER BY favorito DESC, order_index ASC, id ASC"
    ).fetchall()
    # 'b' e favorito -> deve ficar no topo (order_index 0).
    assert rows[0]["id"] == "b"


# ── fix #4: hide_all_done() retorna HideAllDoneResult ─────────────────────────


def test_hide_all_done_returns_structured_result(repo):
    repo.create(_task(id="d1", title="D1", status=Status.DONE))
    repo.create(_task(id="d2", title="D2", status=Status.DONE, permanente=True))
    result = repo.hide_all_done()
    assert isinstance(result, HideAllDoneResult)
    assert result.affected_count == 1
    assert result.excluded_permanente_count == 1


def test_hide_all_done_result_is_int_comparable(repo):
    """Compatibilidade legada: o resultado compara com int via affected_count."""
    repo.create(_task(id="d1", title="D1", status=Status.DONE))
    result = repo.hide_all_done()
    assert result == 1
    assert result > 0
    assert bool(result) is True
    assert int(result) == 1


def test_hide_all_done_zero_result_is_falsy(repo):
    repo.create(_task(id="p", title="P", status=Status.PENDING))
    result = repo.hide_all_done()
    assert result == 0
    assert bool(result) is False
    assert result.excluded_permanente_count == 0


def test_hide_all_done_counts_only_visible_permanentes(repo, conn):
    """excluded_permanente_count conta apenas DONE permanentes ainda visiveis."""
    repo.create(_task(id="p1", title="P1", status=Status.DONE, permanente=True))
    repo.create(_task(id="p2", title="P2", status=Status.DONE, permanente=True))
    # p2 ja oculta -> nao deve contar como "excluida" (ja nao esta visivel).
    conn.execute("UPDATE tasks SET hidden_at = '2026-01-01' WHERE id='p2'")
    conn.commit()
    result = repo.hide_all_done()
    assert result.excluded_permanente_count == 1


# ── fix #5: touch incondicional de updated_at ─────────────────────────────────


def _updated_at(conn, task_id: str):
    return conn.execute(
        "SELECT updated_at FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()["updated_at"]


def test_update_favorito_touches_updated_at(repo, conn):
    """update_favorito muda updated_at (source.md secao 3.4)."""
    repo.create(_task(id="a", title="T"))
    conn.execute("UPDATE tasks SET updated_at = '2000-01-01 00:00:00' WHERE id='a'")
    conn.commit()
    before = _updated_at(conn, "a")
    repo.update_favorito("a", True)
    after = _updated_at(conn, "a")
    assert after is not None
    assert after != before


def test_update_permanente_touches_updated_at(repo, conn):
    """update_permanente muda updated_at (source.md secao 3.4)."""
    repo.create(_task(id="a", title="T"))
    conn.execute("UPDATE tasks SET updated_at = '2000-01-01 00:00:00' WHERE id='a'")
    conn.commit()
    before = _updated_at(conn, "a")
    repo.update_permanente("a", True)
    after = _updated_at(conn, "a")
    assert after is not None
    assert after != before


def test_update_generic_touches_updated_at(repo, conn):
    repo.create(_task(id="a", title="T"))
    conn.execute("UPDATE tasks SET updated_at = '2000-01-01 00:00:00' WHERE id='a'")
    conn.commit()
    before = _updated_at(conn, "a")
    repo.update("a", title="novo")
    after = _updated_at(conn, "a")
    assert after is not None
    assert after != before


def test_update_status_touches_updated_at(repo, conn):
    repo.create(_task(id="a", title="T", status=Status.PENDING))
    conn.execute("UPDATE tasks SET updated_at = '2000-01-01 00:00:00' WHERE id='a'")
    conn.commit()
    before = _updated_at(conn, "a")
    repo.update_status("a", Status.DONE, None)
    after = _updated_at(conn, "a")
    assert after is not None
    assert after != before


# ── fix #6: update_subtask_text ───────────────────────────────────────────────


def _subtask(id: str = "s1", task_id: str = "t1", text: str = "sub", **kw) -> Subtask:
    return Subtask(id=id, task_id=task_id, text=text, **kw)


def test_update_subtask_text_persists(repo):
    repo.create(_task(id="t1", title="T"))
    repo.create_subtask(_subtask(id="s1", task_id="t1", text="original"))
    repo.update_subtask_text("s1", "editado")
    subs = repo.list_subtasks("t1")
    assert subs[0].text == "editado"


def test_update_subtask_text_raises_on_unknown_id(repo):
    """rowcount == 0 -> SubtaskNotFoundError (subtask sumiu)."""
    with pytest.raises(SubtaskNotFoundError):
        repo.update_subtask_text("ghost", "qualquer")


@pytest.mark.parametrize("bad", [None, 123, b"bytes", ["lista"], object()])
def test_update_subtask_text_rejects_non_str(repo, bad):
    repo.create(_task(id="t1", title="T"))
    repo.create_subtask(_subtask(id="s1", task_id="t1"))
    with pytest.raises(ValueError):
        repo.update_subtask_text("s1", bad)


def test_update_subtask_text_accepts_empty_string(repo):
    """String vazia e valida (str) — limpar o texto e permitido."""
    repo.create(_task(id="t1", title="T"))
    repo.create_subtask(_subtask(id="s1", task_id="t1", text="algo"))
    repo.update_subtask_text("s1", "")
    assert repo.list_subtasks("t1")[0].text == ""
