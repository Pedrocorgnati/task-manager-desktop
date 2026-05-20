from __future__ import annotations

import sqlite3
from pathlib import Path

_connection: sqlite3.Connection | None = None

_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('pending', 'in_progress', 'done')),
    type        TEXT NOT NULL DEFAULT 'agent' CHECK (type IN ('agent', 'dev', 'human')),
    projeto     TEXT NOT NULL DEFAULT 'outros',
    deps        TEXT DEFAULT '',
    notes       TEXT DEFAULT '',
    order_index INTEGER DEFAULT 0,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    hidden_at   TIMESTAMP NULL
);

CREATE INDEX IF NOT EXISTS idx_status       ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_completed_at ON tasks(completed_at);
CREATE INDEX IF NOT EXISTS idx_hidden_at    ON tasks(hidden_at);
CREATE INDEX IF NOT EXISTS idx_projeto      ON tasks(projeto);

CREATE TABLE IF NOT EXISTS _schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_MIGRATIONS: list[tuple[int, str]] = [
    (1, _SCHEMA_V1),
    (
        2,
        """
        CREATE TABLE IF NOT EXISTS subtasks (
            id          TEXT PRIMARY KEY,
            task_id     TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            text        TEXT NOT NULL,
            done        INTEGER NOT NULL DEFAULT 0,
            color       TEXT NOT NULL DEFAULT '#FBBF24',
            order_index INTEGER NOT NULL DEFAULT 0,
            created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_subtasks_task_order
            ON subtasks(task_id, order_index);
        """,
    ),
    (
        3,
        """
        PRAGMA foreign_keys=OFF;

        CREATE TABLE IF NOT EXISTS tasks_v3 (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            status      TEXT NOT NULL CHECK (status IN ('pending', 'in_progress', 'done')),
            type        TEXT NOT NULL DEFAULT 'agent' CHECK (type IN ('agent', 'dev', 'human')),
            projeto     TEXT NOT NULL DEFAULT 'outros',
            deps        TEXT DEFAULT '',
            notes       TEXT DEFAULT '',
            order_index INTEGER DEFAULT 0,
            created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL,
            hidden_at   TIMESTAMP NULL
        );

        INSERT OR REPLACE INTO tasks_v3 (
            id, title, status, type, projeto, deps, notes,
            order_index, created_at, completed_at, hidden_at
        )
        SELECT
            id,
            title,
            status,
            CASE type
                WHEN 'online' THEN 'agent'
                WHEN 'offline' THEN 'human'
                WHEN 'agent' THEN 'agent'
                WHEN 'human' THEN 'human'
                ELSE 'agent'
            END,
            projeto,
            deps,
            notes,
            order_index,
            created_at,
            completed_at,
            hidden_at
        FROM tasks;

        DROP TABLE tasks;
        ALTER TABLE tasks_v3 RENAME TO tasks;

        CREATE INDEX IF NOT EXISTS idx_status       ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_completed_at ON tasks(completed_at);
        CREATE INDEX IF NOT EXISTS idx_hidden_at    ON tasks(hidden_at);
        CREATE INDEX IF NOT EXISTS idx_projeto      ON tasks(projeto);

        PRAGMA foreign_keys=ON;
        """,
    ),
    (
        4,
        """
        ALTER TABLE subtasks ADD COLUMN notes TEXT NOT NULL DEFAULT '';
        """,
    ),
    (
        5,
        """
        PRAGMA foreign_keys=OFF;

        CREATE TABLE IF NOT EXISTS tasks_v5 (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            status      TEXT NOT NULL CHECK (status IN ('pending', 'in_progress', 'done')),
            type        TEXT NOT NULL DEFAULT 'agent' CHECK (type IN ('agent', 'dev', 'human')),
            projeto     TEXT NOT NULL DEFAULT 'outros',
            deps        TEXT DEFAULT '',
            notes       TEXT DEFAULT '',
            order_index INTEGER DEFAULT 0,
            created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL,
            hidden_at   TIMESTAMP NULL
        );

        INSERT OR REPLACE INTO tasks_v5 (
            id, title, status, type, projeto, deps, notes,
            order_index, created_at, completed_at, hidden_at
        )
        SELECT
            id,
            title,
            status,
            CASE type
                WHEN 'agent' THEN 'agent'
                WHEN 'dev' THEN 'dev'
                WHEN 'human' THEN 'human'
                ELSE 'agent'
            END,
            projeto,
            deps,
            notes,
            order_index,
            created_at,
            completed_at,
            hidden_at
        FROM tasks;

        DROP TABLE tasks;
        ALTER TABLE tasks_v5 RENAME TO tasks;

        CREATE INDEX IF NOT EXISTS idx_status       ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_completed_at ON tasks(completed_at);
        CREATE INDEX IF NOT EXISTS idx_hidden_at    ON tasks(hidden_at);
        CREATE INDEX IF NOT EXISTS idx_projeto      ON tasks(projeto);

        PRAGMA foreign_keys=ON;
        """,
    ),
    (
        6,
        """
        DROP INDEX IF EXISTS idx_projeto;
        ALTER TABLE tasks DROP COLUMN projeto;
        """,
    ),
]


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Retorna a conexao singleton (thread principal Qt)."""
    global _connection
    if _connection is None:
        if db_path is None:
            raise RuntimeError("get_connection() chamado antes de ensure_data_dir_and_db()")
        _connection = sqlite3.connect(str(db_path))
        _connection.row_factory = sqlite3.Row
    return _connection


def run_migrations(conn: sqlite3.Connection) -> None:
    """Aplica migrations pendentes. Idempotente — seguro chamar multiplas vezes."""
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS _schema_version "
        "(version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.commit()

    applied = {row[0] for row in cursor.execute("SELECT version FROM _schema_version")}

    for version, ddl in _MIGRATIONS:
        if version in applied:
            continue
        conn.executescript(ddl)
        cursor.execute("INSERT INTO _schema_version (version) VALUES (?)", (version,))
        conn.commit()


def validate_database(conn: sqlite3.Connection) -> None:
    """Executa PRAGMA integrity_check. Levanta DatabaseError se banco estiver corrompido."""
    row = conn.execute("PRAGMA integrity_check").fetchone()
    result = row[0] if row else "error"
    if result != "ok":
        raise sqlite3.DatabaseError(f"integrity_check falhou: {result}")


def close_connection() -> None:
    """Fecha e limpa a conexao singleton (para uso em testes)."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
