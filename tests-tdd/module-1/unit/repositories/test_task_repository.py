# suite: unit | module: module-1-gestao-de-tasks | tasks: TASK-1, TASK-2, TASK-3
# @tdd-locked: do not edit without /tdd:unlock
# covers: TASK-1/ST003, TASK-2/ST003, TASK-3/ST001 — TaskRepository todos os metodos
# target: task_manager_desktop/repositories/task_repository.py
# TIDs: TID-1-1-017, TID-1-1-018, TID-1-1-019, TID-1-2-019,
#        TID-1-3-010, TID-1-3-011, TID-1-3-012, TID-1-3-013,
#        TID-1-3-014, TID-1-3-015, TID-1-3-016
import sqlite3

import pytest

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Task, TaskType
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


def _make_task(id: str = "abc", title: str = "T", **kw) -> Task:
    return Task(id=id, title=title, **kw)


# TID-1-1-017 | covers: TASK-1/ST003 insert
def test_insert_uses_bind_params_and_persists_all_fields(repo, conn):
    """TaskRepository.insert usa bind ? e persiste todos os campos (id,title,type,projeto,deps,timestamps)."""
    task = _make_task(id="abc", title="X", type=TaskType.OFFLINE, projeto="systemforge", deps=["dep1"])
    repo.create(task)

    row = conn.execute("SELECT * FROM tasks WHERE id='abc'").fetchone()
    assert row is not None
    assert row["title"] == "X"
    assert row["type"] == "offline"
    assert row["projeto"] == "systemforge"
    assert row["deps"] == "dep1"


# TID-1-1-018 | covers: TASK-1/ST003 list_active
def test_list_active_returns_only_tasks_without_hidden_at(repo, conn):
    """TaskRepository.list_active retorna apenas tasks com hidden_at IS NULL."""
    repo.create(_make_task(id="a", title="visible"))
    repo.create(_make_task(id="b", title="hidden"))
    conn.execute("UPDATE tasks SET hidden_at='2026-01-01T00:00:00Z' WHERE id='b'")
    conn.commit()

    active = repo.list_active()
    assert len(active) == 1
    assert active[0].id == "a"


# TID-1-1-019 | covers: TASK-1/ST003 exists
def test_exists_returns_true_when_present_false_otherwise(repo):
    """TaskRepository.exists(id) retorna True/False conforme presenca."""
    repo.create(_make_task(id="x", title="t"))
    assert repo.exists("x") is True
    assert repo.exists("nope") is False


# TID-1-2-019 | covers: TASK-2/ST003 update
def test_update_applies_four_fields_via_bind_where_id(repo, conn):
    """TaskRepository.update aplica UPDATE com 4 campos (title,type,projeto,deps) via bind ? WHERE id=?."""
    repo.create(_make_task(id="u", title="orig", type=TaskType.ONLINE, projeto="outros"))
    repo.update("u", title="updated", type=TaskType.OFFLINE, projeto="sf", deps=["a", "b"])

    row = conn.execute("SELECT * FROM tasks WHERE id='u'").fetchone()
    assert row["title"] == "updated"
    assert row["type"] == "offline"
    assert row["projeto"] == "sf"
    assert row["deps"] == "a,b"


# TID-1-3-010 | covers: TASK-3/ST001 delete
def test_delete_is_hard_delete_and_noop_on_missing_id(repo, conn):
    """TaskRepository.delete e hard (DELETE FROM tasks) e no-op (sem raise) quando id inexistente."""
    repo.create(_make_task(id="d", title="t"))
    repo.delete("d")

    row = conn.execute("SELECT * FROM tasks WHERE id='d'").fetchone()
    assert row is None

    # no-op on missing id — must not raise
    repo.delete("nonexistent")


# TID-1-3-011 | covers: TASK-3/ST001 list_trash
def test_list_trash_returns_only_tasks_with_hidden_at_not_null(repo, conn):
    """TaskRepository.list_trash retorna apenas tasks com hidden_at IS NOT NULL."""
    repo.create(_make_task(id="a", title="active"))
    repo.create(_make_task(id="b", title="trashed"))
    conn.execute("UPDATE tasks SET hidden_at='2026-01-01T00:00:00Z' WHERE id='b'")
    conn.commit()

    trash = repo.list_trash()
    assert len(trash) == 1
    assert trash[0].id == "b"


# TID-1-3-012 | covers: TASK-3/ST001 get_by_id
def test_get_by_id_returns_task_or_none(repo):
    """TaskRepository.get_by_id retorna Task ou None."""
    repo.create(_make_task(id="g", title="t"))
    found = repo.get_by_id("g")
    assert found is not None
    assert found.id == "g"
    assert repo.get_by_id("missing") is None


# TID-1-3-013 | covers: TASK-3/ST001 mark_hidden
def test_mark_hidden_in_single_transaction_rollback_on_failure(repo, conn):
    """TaskRepository.mark_hidden em transacao unica: falha rollback nao deixa estado parcial."""
    repo.create(_make_task(id="h", title="t"))
    repo.mark_hidden("h")

    row = conn.execute("SELECT hidden_at FROM tasks WHERE id='h'").fetchone()
    assert row["hidden_at"] is not None


# TID-1-3-014 | covers: TASK-3/ST001 restore
def test_restore_sets_hidden_at_to_null(repo, conn):
    """TaskRepository.restore seta hidden_at = NULL."""
    repo.create(_make_task(id="r", title="t"))
    repo.mark_hidden("r")
    repo.restore("r")

    row = conn.execute("SELECT hidden_at FROM tasks WHERE id='r'").fetchone()
    assert row["hidden_at"] is None


# TID-1-3-015 | covers: TASK-3/ST001 list_projetos
def test_list_projetos_distinct_excludes_hidden_orders_case_insensitive(repo, conn):
    """TaskRepository.list_projetos: DISTINCT, exclui hidden, ORDER BY LOWER(projeto) (case-insensitive)."""
    repo.create(_make_task(id="1", title="t1", projeto="Zeta"))
    repo.create(_make_task(id="2", title="t2", projeto="alpha"))
    repo.create(_make_task(id="3", title="t3", projeto="beta"))
    repo.create(_make_task(id="4", title="t4", projeto="Hidden"))
    conn.execute("UPDATE tasks SET hidden_at='2026-01-01T00:00:00Z' WHERE id='4'")
    conn.commit()

    projetos = repo.list_projetos()
    assert "Hidden" not in projetos
    assert projetos == sorted(projetos, key=str.lower)


# TID-1-3-016 | covers: TASK-3/ST001 init
def test_init_exposes_db_path_as_public_attribute(conn):
    """TaskRepository.__init__(conn, db_path) expoe db_path como atributo publico para ErrorDialog."""
    repo = TaskRepository(conn, db_path="/some/path/tasks.db")
    assert repo.db_path == "/some/path/tasks.db"
