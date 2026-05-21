"""Testes de favorito/permanente no TaskRepository (loop 05-20 TASK-008).

Cobre: persistencia round-trip dos flags, casting explicito em _row_to_task,
contratos de update_favorito/update_permanente (TaskNotFoundError em id
inexistente, validacao de range booleano com ValueError) e o filtro da
vassoura hide_all_done excluindo tasks permanentes.
"""

from __future__ import annotations

import sqlite3

import pytest

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.exceptions import TaskNotFoundError
from task_manager_desktop.core.models import Status, Task
from task_manager_desktop.repositories.task_repository import TaskRepository


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


# ── round-trip persistence ────────────────────────────────────────────────────


def test_create_defaults_flags_to_false(repo):
    repo.create(_task(id="a", title="T"))
    task = repo.get_by_id("a")
    assert task is not None
    assert task.favorito is False
    assert task.permanente is False


def test_create_persists_flags_true(repo):
    repo.create(_task(id="a", title="T", favorito=True, permanente=True))
    task = repo.get_by_id("a")
    assert task is not None
    assert task.favorito is True
    assert task.permanente is True


def test_row_to_task_casts_flags_to_bool(repo, conn):
    """_row_to_task aplica bool(int(...)); leitura de 0/1 vira False/True reais."""
    repo.create(_task(id="a", title="T", favorito=True))
    task = repo.get_by_id("a")
    assert task is not None
    assert isinstance(task.favorito, bool)
    assert isinstance(task.permanente, bool)


def test_update_favorito_toggles_value(repo):
    repo.create(_task(id="a", title="T"))
    repo.update_favorito("a", True)
    assert repo.get_by_id("a").favorito is True
    repo.update_favorito("a", False)
    assert repo.get_by_id("a").favorito is False


def test_update_permanente_toggles_value(repo):
    repo.create(_task(id="a", title="T"))
    repo.update_permanente("a", True)
    assert repo.get_by_id("a").permanente is True
    repo.update_permanente("a", False)
    assert repo.get_by_id("a").permanente is False


def test_update_generic_persists_flags(repo):
    repo.create(_task(id="a", title="T"))
    repo.update("a", favorito=True, permanente=True)
    task = repo.get_by_id("a")
    assert task.favorito is True
    assert task.permanente is True


# ── TaskNotFoundError em id inexistente ───────────────────────────────────────


def test_update_favorito_raises_on_unknown_id(repo):
    with pytest.raises(TaskNotFoundError):
        repo.update_favorito("ghost", True)


def test_update_permanente_raises_on_unknown_id(repo):
    with pytest.raises(TaskNotFoundError):
        repo.update_permanente("ghost", True)


# ── validacao de range booleano (ValueError) ──────────────────────────────────


@pytest.mark.parametrize("bad_value", [1, 0, "true", None, 2])
def test_update_favorito_rejects_non_bool(repo, bad_value):
    repo.create(_task(id="a", title="T"))
    with pytest.raises(ValueError):
        repo.update_favorito("a", bad_value)


@pytest.mark.parametrize("bad_value", [1, 0, "false", None, 2])
def test_update_permanente_rejects_non_bool(repo, bad_value):
    repo.create(_task(id="a", title="T"))
    with pytest.raises(ValueError):
        repo.update_permanente("a", bad_value)


def test_create_rejects_non_bool_flag(repo):
    with pytest.raises(ValueError):
        repo.create(_task(id="a", title="T", favorito=1))


def test_update_generic_rejects_non_bool_flag(repo):
    repo.create(_task(id="a", title="T"))
    with pytest.raises(ValueError):
        repo.update("a", permanente="yes")


# ── AC-11: update_permanente des-oculta task DONE (source.md secao 1.9) ───────


def test_update_permanente_unhides_done_task(repo, conn):
    """Ligar permanente em task DONE oculta zera hidden_at (qualifica p/ PERMANENT)."""
    repo.create(_task(id="a", title="T", status=Status.DONE))
    conn.execute(
        "UPDATE tasks SET hidden_at = ? WHERE id = ?",
        ("2026-05-20T12:00:00+00:00", "a"),
    )
    conn.commit()
    repo.update_permanente("a", True)
    row = conn.execute("SELECT hidden_at, permanente FROM tasks WHERE id='a'").fetchone()
    assert row["hidden_at"] is None
    assert row["permanente"] == 1


def test_update_permanente_preserves_hidden_at_when_not_done(repo, conn):
    """Ligar permanente em task NAO-DONE oculta preserva hidden_at (nao qualifica)."""
    repo.create(_task(id="a", title="T", status=Status.PENDING))
    conn.execute(
        "UPDATE tasks SET hidden_at = ? WHERE id = ?",
        ("2026-05-20T12:00:00+00:00", "a"),
    )
    conn.commit()
    repo.update_permanente("a", True)
    row = conn.execute("SELECT hidden_at FROM tasks WHERE id='a'").fetchone()
    assert row["hidden_at"] == "2026-05-20T12:00:00+00:00"


def test_update_permanente_false_preserves_hidden_at_on_done(repo, conn):
    """Desligar permanente nunca zera hidden_at, mesmo em task DONE."""
    repo.create(_task(id="a", title="T", status=Status.DONE, permanente=True))
    conn.execute(
        "UPDATE tasks SET hidden_at = ? WHERE id = ?",
        ("2026-05-20T12:00:00+00:00", "a"),
    )
    conn.commit()
    repo.update_permanente("a", False)
    row = conn.execute("SELECT hidden_at FROM tasks WHERE id='a'").fetchone()
    assert row["hidden_at"] == "2026-05-20T12:00:00+00:00"


def test_update_favorito_never_touches_hidden_at(repo, conn):
    """Favorito jamais afeta hidden_at, nem em task DONE oculta."""
    repo.create(_task(id="a", title="T", status=Status.DONE))
    conn.execute(
        "UPDATE tasks SET hidden_at = ? WHERE id = ?",
        ("2026-05-20T12:00:00+00:00", "a"),
    )
    conn.commit()
    repo.update_favorito("a", True)
    row = conn.execute("SELECT hidden_at FROM tasks WHERE id='a'").fetchone()
    assert row["hidden_at"] == "2026-05-20T12:00:00+00:00"


def test_update_generic_permanente_unhides_done_task(repo, conn):
    """O UPDATE generico (usado pelo EditTaskController) tambem des-oculta DONE."""
    repo.create(_task(id="a", title="T", status=Status.DONE))
    conn.execute(
        "UPDATE tasks SET hidden_at = ? WHERE id = ?",
        ("2026-05-20T12:00:00+00:00", "a"),
    )
    conn.commit()
    repo.update("a", permanente=True)
    row = conn.execute("SELECT hidden_at FROM tasks WHERE id='a'").fetchone()
    assert row["hidden_at"] is None


def test_update_generic_permanente_preserves_hidden_at_when_not_done(repo, conn):
    """UPDATE generico preserva hidden_at quando o status nao qualifica."""
    repo.create(_task(id="a", title="T", status=Status.PENDING))
    conn.execute(
        "UPDATE tasks SET hidden_at = ? WHERE id = ?",
        ("2026-05-20T12:00:00+00:00", "a"),
    )
    conn.commit()
    repo.update("a", permanente=True)
    row = conn.execute("SELECT hidden_at FROM tasks WHERE id='a'").fetchone()
    assert row["hidden_at"] == "2026-05-20T12:00:00+00:00"


# ── vassoura hide_all_done exclui permanentes ─────────────────────────────────


def test_hide_all_done_skips_permanent_tasks(repo, conn):
    repo.create(_task(id="done_normal", title="N", status=Status.DONE))
    repo.create(
        _task(id="done_perm", title="P", status=Status.DONE, permanente=True)
    )
    hidden_count = repo.hide_all_done()
    assert hidden_count == 1

    normal = conn.execute(
        "SELECT hidden_at FROM tasks WHERE id='done_normal'"
    ).fetchone()
    perm = conn.execute(
        "SELECT hidden_at FROM tasks WHERE id='done_perm'"
    ).fetchone()
    assert normal["hidden_at"] is not None
    assert perm["hidden_at"] is None


def test_hide_all_done_ignores_non_done_tasks(repo):
    repo.create(_task(id="pending", title="P", status=Status.PENDING))
    assert repo.hide_all_done() == 0
