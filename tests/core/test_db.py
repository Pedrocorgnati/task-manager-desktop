import sqlite3

import pytest

from task_manager_desktop.core.db import run_migrations


def test_schema_v1_creates_tasks_table(in_memory_db):
    run_migrations(in_memory_db)
    cursor = in_memory_db.execute("PRAGMA table_info(tasks)")
    columns = {row[1] for row in cursor}
    expected = {
        "id", "title", "status", "type", "deps", "notes",
        "order_index", "created_at", "completed_at", "hidden_at",
        # v7: campos favorito/permanente + updated_at (touch em update_*)
        "favorito", "permanente", "updated_at",
    }
    assert expected == columns


def test_schema_v1_creates_indices(in_memory_db):
    run_migrations(in_memory_db)
    cursor = in_memory_db.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='tasks'"
        " AND name NOT LIKE 'sqlite_autoindex_%'"
    )
    indices = {row[0] for row in cursor}
    assert {"idx_status", "idx_completed_at", "idx_hidden_at"} == indices


def test_schema_version_row_inserted(in_memory_db):
    run_migrations(in_memory_db)
    row = in_memory_db.execute("SELECT version FROM _schema_version").fetchone()
    assert row is not None
    assert row[0] == 1


def test_migration_is_idempotent(in_memory_db):
    run_migrations(in_memory_db)
    run_migrations(in_memory_db)
    count = in_memory_db.execute("SELECT COUNT(*) FROM _schema_version").fetchone()[0]
    assert count == 7


def test_migration_v3_converts_legacy_online_offline_values(in_memory_db):
    in_memory_db.executescript(
        """
        CREATE TABLE tasks (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            status      TEXT NOT NULL CHECK (status IN ('pending', 'in_progress', 'done')),
            type        TEXT NOT NULL DEFAULT 'online' CHECK (type IN ('online', 'offline')),
            projeto     TEXT NOT NULL DEFAULT 'outros',
            deps        TEXT DEFAULT '',
            notes       TEXT DEFAULT '',
            order_index INTEGER DEFAULT 0,
            created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL,
            hidden_at   TIMESTAMP NULL
        );
        CREATE TABLE _schema_version (
            version    INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE subtasks (
            id          TEXT PRIMARY KEY,
            task_id     TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            text        TEXT NOT NULL,
            done        INTEGER NOT NULL DEFAULT 0,
            color       TEXT NOT NULL DEFAULT '#FBBF24',
            order_index INTEGER NOT NULL DEFAULT 0,
            created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO _schema_version (version) VALUES (1);
        INSERT INTO _schema_version (version) VALUES (2);
        INSERT INTO tasks (id, title, status, type) VALUES ('a', 'A', 'pending', 'online');
        INSERT INTO tasks (id, title, status, type) VALUES ('h', 'H', 'pending', 'offline');
        """
    )

    run_migrations(in_memory_db)

    rows = {
        row["id"]: row["type"]
        for row in in_memory_db.execute("SELECT id, type FROM tasks ORDER BY id")
    }
    assert rows == {"a": "agent", "h": "human"}
    with pytest.raises(sqlite3.IntegrityError):
        in_memory_db.execute(
            "INSERT INTO tasks (id, title, status, type) VALUES ('old', 'Old', 'pending', 'online')"
        )


def test_migration_v4_adds_subtask_notes_column(in_memory_db):
    run_migrations(in_memory_db)
    columns = {row["name"] for row in in_memory_db.execute("PRAGMA table_info(subtasks)")}
    assert "notes" in columns


def test_type_check_constraint_accepts_dev(in_memory_db):
    run_migrations(in_memory_db)
    in_memory_db.execute(
        "INSERT INTO tasks (id, title, status, type) VALUES ('dev1', 'Dev', 'pending', 'dev')"
    )
    in_memory_db.commit()
    row = in_memory_db.execute("SELECT type FROM tasks WHERE id='dev1'").fetchone()
    assert row["type"] == "dev"


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


def test_type_defaults_to_agent(in_memory_db):
    run_migrations(in_memory_db)
    in_memory_db.execute(
        "INSERT INTO tasks (id, title, status) VALUES ('a1b', 'T', 'pending')"
    )
    in_memory_db.commit()
    row = in_memory_db.execute("SELECT type FROM tasks WHERE id='a1b'").fetchone()
    assert row["type"] == "agent"


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
