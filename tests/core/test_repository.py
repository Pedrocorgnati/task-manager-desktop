from __future__ import annotations

import sqlite3

import pytest

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Status, Task, TaskType
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


# ── create ───────────────────────────────────────────────────────────────────


def test_create_persists_all_fields(repo, conn):
    task = _task(
        id="abc",
        title="Tarefa X",
        type=TaskType.OFFLINE,
        projeto="forge",
        deps=["d1", "d2"],
        notes="nota",
    )
    repo.create(task)

    row = conn.execute("SELECT * FROM tasks WHERE id='abc'").fetchone()
    assert row is not None
    assert row["title"] == "Tarefa X"
    assert row["type"] == "offline"
    assert row["projeto"] == "forge"
    assert row["deps"] == "d1,d2"
    assert row["notes"] == "nota"


def test_create_empty_deps_stored_as_empty_string(repo, conn):
    repo.create(_task(id="x", title="T", deps=[]))
    row = conn.execute("SELECT deps FROM tasks WHERE id='x'").fetchone()
    assert row["deps"] == ""


# ── update ───────────────────────────────────────────────────────────────────


def test_update_changes_title(repo, conn):
    repo.create(_task(id="u", title="orig"))
    repo.update("u", title="novo")
    row = conn.execute("SELECT title FROM tasks WHERE id='u'").fetchone()
    assert row["title"] == "novo"


def test_update_deps_list_converted_to_csv(repo, conn):
    repo.create(_task(id="u", title="t"))
    repo.update("u", deps=["a", "b"])
    row = conn.execute("SELECT deps FROM tasks WHERE id='u'").fetchone()
    assert row["deps"] == "a,b"


def test_update_status_enum_stored_as_value(repo, conn):
    repo.create(_task(id="u", title="t"))
    repo.update("u", status=Status.DONE)
    row = conn.execute("SELECT status FROM tasks WHERE id='u'").fetchone()
    assert row["status"] == "done"


def test_update_type_enum_stored_as_value(repo, conn):
    repo.create(_task(id="u", title="t"))
    repo.update("u", type=TaskType.OFFLINE)
    row = conn.execute("SELECT type FROM tasks WHERE id='u'").fetchone()
    assert row["type"] == "offline"


def test_update_projeto_normalizes(repo, conn):
    repo.create(_task(id="u", title="t"))
    repo.update("u", projeto="  ")
    row = conn.execute("SELECT projeto FROM tasks WHERE id='u'").fetchone()
    assert row["projeto"] == "outros"


def test_update_ignores_unknown_keys(repo, conn):
    repo.create(_task(id="u", title="orig"))
    repo.update("u", unknown_field="value")
    row = conn.execute("SELECT title FROM tasks WHERE id='u'").fetchone()
    assert row["title"] == "orig"


def test_update_with_no_valid_fields_is_noop(repo, conn):
    repo.create(_task(id="u", title="stable"))
    repo.update("u")
    row = conn.execute("SELECT title FROM tasks WHERE id='u'").fetchone()
    assert row["title"] == "stable"


# ── delete ────────────────────────────────────────────────────────────────────


def test_delete_removes_row_permanently(repo, conn):
    repo.create(_task(id="d", title="t"))
    repo.delete("d")
    row = conn.execute("SELECT * FROM tasks WHERE id='d'").fetchone()
    assert row is None


def test_delete_noop_on_nonexistent_id(repo):
    # Must not raise
    repo.delete("ghost")


def test_delete_does_not_affect_other_rows(repo, conn):
    repo.create(_task(id="a", title="keep"))
    repo.create(_task(id="b", title="remove"))
    repo.delete("b")
    assert conn.execute("SELECT * FROM tasks WHERE id='a'").fetchone() is not None
    assert conn.execute("SELECT * FROM tasks WHERE id='b'").fetchone() is None


# ── list_active ───────────────────────────────────────────────────────────────


def test_list_active_returns_only_non_hidden(repo, conn):
    repo.create(_task(id="a", title="visible"))
    repo.create(_task(id="b", title="hidden"))
    conn.execute("UPDATE tasks SET hidden_at='2026-01-01T00:00:00Z' WHERE id='b'")
    conn.commit()

    active = repo.list_active()
    ids = [t.id for t in active]
    assert "a" in ids
    assert "b" not in ids


def test_list_active_empty_returns_empty_list(repo):
    assert repo.list_active() == []


def test_list_active_returns_task_objects(repo):
    repo.create(_task(id="a", title="T"))
    result = repo.list_active()
    assert len(result) == 1
    assert isinstance(result[0], Task)


# ── list_trash ────────────────────────────────────────────────────────────────


def test_list_trash_returns_only_hidden_tasks(repo, conn):
    repo.create(_task(id="a", title="active"))
    repo.create(_task(id="b", title="trashed"))
    conn.execute("UPDATE tasks SET hidden_at='2026-01-01T00:00:00Z' WHERE id='b'")
    conn.commit()

    trash = repo.list_trash()
    assert len(trash) == 1
    assert trash[0].id == "b"


def test_list_trash_empty_when_no_hidden(repo):
    repo.create(_task(id="a", title="T"))
    assert repo.list_trash() == []


# ── get_by_id ─────────────────────────────────────────────────────────────────


def test_get_by_id_returns_task_when_found(repo):
    repo.create(_task(id="g", title="T"))
    result = repo.get_by_id("g")
    assert result is not None
    assert result.id == "g"


def test_get_by_id_returns_none_when_not_found(repo):
    assert repo.get_by_id("missing") is None


# ── mark_hidden ───────────────────────────────────────────────────────────────


def test_mark_hidden_sets_hidden_at(repo, conn):
    repo.create(_task(id="h", title="t"))
    repo.mark_hidden("h")
    row = conn.execute("SELECT hidden_at FROM tasks WHERE id='h'").fetchone()
    assert row["hidden_at"] is not None


def test_mark_hidden_task_no_longer_in_list_active(repo):
    repo.create(_task(id="h", title="t"))
    repo.mark_hidden("h")
    ids = [t.id for t in repo.list_active()]
    assert "h" not in ids


# ── restore ───────────────────────────────────────────────────────────────────


def test_restore_sets_hidden_at_to_null(repo, conn):
    repo.create(_task(id="r", title="t"))
    repo.mark_hidden("r")
    repo.restore("r")
    row = conn.execute("SELECT hidden_at FROM tasks WHERE id='r'").fetchone()
    assert row["hidden_at"] is None


def test_restore_makes_task_appear_in_list_active(repo):
    repo.create(_task(id="r", title="t"))
    repo.mark_hidden("r")
    repo.restore("r")
    ids = [t.id for t in repo.list_active()]
    assert "r" in ids


# ── list_projetos ─────────────────────────────────────────────────────────────


def test_list_projetos_empty_db_returns_empty_list(repo):
    assert repo.list_projetos() == []


def test_list_projetos_distinct_values(repo):
    repo.create(_task(id="1", title="t1", projeto="alpha"))
    repo.create(_task(id="2", title="t2", projeto="alpha"))
    repo.create(_task(id="3", title="t3", projeto="beta"))
    result = repo.list_projetos()
    assert result.count("alpha") == 1
    assert "beta" in result


def test_list_projetos_excludes_hidden(repo, conn):
    repo.create(_task(id="1", title="t1", projeto="visible"))
    repo.create(_task(id="2", title="t2", projeto="secret"))
    conn.execute("UPDATE tasks SET hidden_at='2026-01-01T00:00:00Z' WHERE id='2'")
    conn.commit()
    result = repo.list_projetos()
    assert "secret" not in result
    assert "visible" in result


def test_list_projetos_ordered_case_insensitive(repo):
    repo.create(_task(id="1", title="t1", projeto="Zeta"))
    repo.create(_task(id="2", title="t2", projeto="alpha"))
    repo.create(_task(id="3", title="t3", projeto="Beta"))
    result = repo.list_projetos()
    assert result == sorted(result, key=str.lower)


# ── exists ────────────────────────────────────────────────────────────────────


def test_exists_returns_true_when_present(repo):
    repo.create(_task(id="e", title="t"))
    assert repo.exists("e") is True


def test_exists_returns_false_when_absent(repo):
    assert repo.exists("nope") is False
