import sqlite3

import pytest

from task_manager_desktop.core.db import run_migrations


def test_schema_v1_creates_tasks_table(in_memory_db):
    run_migrations(in_memory_db)
    cursor = in_memory_db.execute("PRAGMA table_info(tasks)")
    columns = {row[1] for row in cursor}
    expected = {
        "id", "title", "status", "type", "projeto", "deps", "notes",
        "order_index", "created_at", "completed_at", "hidden_at",
    }
    assert expected == columns


def test_schema_v1_creates_indices(in_memory_db):
    run_migrations(in_memory_db)
    cursor = in_memory_db.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='tasks'"
        " AND name NOT LIKE 'sqlite_autoindex_%'"
    )
    indices = {row[0] for row in cursor}
    assert {"idx_status", "idx_completed_at", "idx_hidden_at", "idx_projeto"} == indices


def test_schema_version_row_inserted(in_memory_db):
    run_migrations(in_memory_db)
    row = in_memory_db.execute("SELECT version FROM _schema_version").fetchone()
    assert row is not None
    assert row[0] == 1


def test_migration_is_idempotent(in_memory_db):
    run_migrations(in_memory_db)
    run_migrations(in_memory_db)
    count = in_memory_db.execute("SELECT COUNT(*) FROM _schema_version").fetchone()[0]
    assert count == 1


def test_status_check_constraint(in_memory_db):
    run_migrations(in_memory_db)
    with pytest.raises(sqlite3.IntegrityError):
        in_memory_db.execute(
            "INSERT INTO tasks (id, title, status) VALUES ('a1b', 'T', 'invalid')"
        )


def test_type_check_constraint(in_memory_db):
    run_migrations(in_memory_db)
    with pytest.raises(sqlite3.IntegrityError):
        in_memory_db.execute(
            "INSERT INTO tasks (id, title, status, type) VALUES ('a1b', 'T', 'pending', 'bad')"
        )


def test_projeto_defaults_to_outros(in_memory_db):
    run_migrations(in_memory_db)
    in_memory_db.execute(
        "INSERT INTO tasks (id, title, status) VALUES ('a1b', 'T', 'pending')"
    )
    in_memory_db.commit()
    row = in_memory_db.execute("SELECT projeto, type FROM tasks WHERE id='a1b'").fetchone()
    assert row["projeto"] == "outros"
    assert row["type"] == "online"


def test_schema_version_table_name_has_underscore_prefix(in_memory_db):
    """AC-T-003: tabela deve ser _schema_version (com underscore)."""
    run_migrations(in_memory_db)
    tables = {
        row[0]
        for row in in_memory_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "_schema_version" in tables
    assert "schema_version" not in tables


def test_get_connection_without_path_raises_when_not_initialized():
    """get_connection() sem db_path raises RuntimeError se ainda nao inicializado."""
    from task_manager_desktop.core.db import close_connection, get_connection
    close_connection()
    with pytest.raises(RuntimeError, match="chamado antes de ensure_data_dir_and_db"):
        get_connection()
