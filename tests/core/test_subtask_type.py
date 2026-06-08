from __future__ import annotations

import sqlite3

import pytest

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Subtask, Task, TaskType
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


def test_subtask_model_defaults_to_agent_type():
    subtask = Subtask(id="s", task_id="t", text="x")
    assert subtask.type is TaskType.AGENT


def test_migration_v9_adds_type_column_and_bumps_user_version(conn):
    cols = {row[1] for row in conn.execute("PRAGMA table_info(subtasks)")}
    assert "type" in cols
    assert conn.execute("PRAGMA user_version").fetchone()[0] >= 9
    applied = {row[0] for row in conn.execute("SELECT version FROM _schema_version")}
    assert 9 in applied


def test_run_migrations_is_idempotent_for_v9(conn):
    # Re-rodar nao deve duplicar a versao nem levantar erro (coluna ja existe).
    run_migrations(conn)
    run_migrations(conn)
    versions = [row[0] for row in conn.execute("SELECT version FROM _schema_version")]
    assert versions.count(9) == 1


@pytest.mark.parametrize(
    "subtask_type",
    [TaskType.AGENT, TaskType.DEV, TaskType.HUMAN],
)
def test_create_subtask_round_trips_type(repo, subtask_type):
    repo.create(Task(id="a", title="A"))
    repo.create_subtask(
        Subtask(id="s0", task_id="a", text="S0", type=subtask_type)
    )
    [loaded] = repo.list_subtasks("a")
    assert loaded.type is subtask_type


def test_legacy_row_without_type_defaults_to_agent(repo, conn):
    repo.create(Task(id="a", title="A"))
    # Insere direto omitindo `type` (coluna tem DEFAULT 'agent' NOT NULL).
    conn.execute(
        "INSERT INTO subtasks (id, task_id, text, done, color, order_index, notes) "
        "VALUES ('legacy', 'a', 'L', 0, '#FBBF24', 1, '')"
    )
    conn.commit()
    [loaded] = repo.list_subtasks("a")
    assert loaded.type is TaskType.AGENT


def test_update_subtask_type_persists(repo):
    repo.create(Task(id="a", title="A"))
    repo.create_subtask(Subtask(id="s0", task_id="a", text="S0"))
    repo.update_subtask_type("s0", TaskType.DEV)
    assert repo.list_subtasks("a")[0].type is TaskType.DEV
    # Aceita tambem a string canonica.
    repo.update_subtask_type("s0", "human")
    assert repo.list_subtasks("a")[0].type is TaskType.HUMAN


def test_update_subtask_type_rejects_invalid_value(repo):
    repo.create(Task(id="a", title="A"))
    repo.create_subtask(Subtask(id="s0", task_id="a", text="S0"))
    with pytest.raises(ValueError):
        repo.update_subtask_type("s0", "robot")


def test_update_subtask_type_raises_on_missing_subtask(repo):
    from task_manager_desktop.repositories.task_repository import SubtaskNotFoundError

    repo.create(Task(id="a", title="A"))
    with pytest.raises(SubtaskNotFoundError):
        repo.update_subtask_type("ghost", TaskType.DEV)


def test_delete_done_subtasks_scoped_by_type(repo):
    repo.create(Task(id="a", title="A"))
    repo.create_subtask(Subtask(id="ag", task_id="a", text="agent done", state=2, type=TaskType.AGENT))
    repo.create_subtask(Subtask(id="dv", task_id="a", text="dev done", state=2, type=TaskType.DEV))

    # Sob filtro "agent", limpar concluidas NAO pode apagar a dev oculta.
    removed = repo.delete_done_subtasks("a", types={"agent"})
    assert removed == 1
    remaining = {s.id for s in repo.list_subtasks("a")}
    assert remaining == {"dv"}


def test_delete_done_subtasks_no_types_removes_all(repo):
    repo.create(Task(id="a", title="A"))
    repo.create_subtask(Subtask(id="ag", task_id="a", text="x", state=2, type=TaskType.AGENT))
    repo.create_subtask(Subtask(id="dv", task_id="a", text="y", state=2, type=TaskType.DEV))
    assert repo.delete_done_subtasks("a") == 2
    assert repo.list_subtasks("a") == []


def test_subtask_types_by_task_groups_distinct_types(repo):
    repo.create(Task(id="a", title="A"))
    repo.create(Task(id="b", title="B"))
    repo.create(Task(id="c", title="C"))  # sem subtasks
    repo.create_subtask(Subtask(id="a1", task_id="a", text="x", type=TaskType.AGENT))
    repo.create_subtask(Subtask(id="a2", task_id="a", text="y", type=TaskType.DEV))
    repo.create_subtask(Subtask(id="a3", task_id="a", text="z", type=TaskType.AGENT))
    repo.create_subtask(Subtask(id="b1", task_id="b", text="w", type=TaskType.HUMAN))

    mapping = repo.subtask_types_by_task()
    assert mapping["a"] == {"agent", "dev"}
    assert mapping["b"] == {"human"}
    # Tasks sem subtasks nao aparecem no mapa.
    assert "c" not in mapping
