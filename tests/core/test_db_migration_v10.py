"""Testes da migracao v9 -> v10 (drop hardened da coluna tasks.type) e do
habilitar de foreign_keys na conexao singleton.

Validam: drop da coluna, preservacao de dados/flags/subtasks, backup
obrigatorio, idempotencia/reentrancia, abort atomico sob lock concorrente, e o
cascade de delete (anti-orfaos) via get_connection.
"""

from __future__ import annotations

import sqlite3

import pytest

from task_manager_desktop.core import db as dbmod
from task_manager_desktop.core.db import (
    _apply_migration_v10,
    close_connection,
    get_connection,
    run_migrations,
)
from task_manager_desktop.core.exceptions import MigrationError
from task_manager_desktop.core.models import Subtask, Task
from task_manager_desktop.repositories.task_repository import TaskRepository

_TASKS_WITH_TYPE = """
CREATE TABLE _schema_version (version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE tasks (
    id TEXT PRIMARY KEY, title TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','in_progress','done')),
    type TEXT NOT NULL DEFAULT 'agent' CHECK (type IN ('agent','dev','human')),
    deps TEXT DEFAULT '', notes TEXT DEFAULT '', order_index INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP NULL, hidden_at TIMESTAMP NULL,
    favorito INTEGER NOT NULL DEFAULT 0 CHECK (favorito IN (0,1)),
    permanente INTEGER NOT NULL DEFAULT 0 CHECK (permanente IN (0,1)),
    updated_at TEXT, em_preparacao INTEGER NOT NULL DEFAULT 0 CHECK (em_preparacao IN (0,1)));
CREATE TABLE subtasks (
    id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    text TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0, color TEXT NOT NULL DEFAULT '#FBBF24',
    order_index INTEGER NOT NULL DEFAULT 0, notes TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL DEFAULT 'agent' CHECK (type IN ('agent','dev','human')));
INSERT INTO _schema_version (version) VALUES (1),(2),(3),(4),(5),(6),(7),(8),(9);
"""


def _build_v9_db(path, seed=True) -> None:
    conn = sqlite3.connect(str(path))
    conn.executescript(_TASKS_WITH_TYPE)
    if seed:
        conn.execute(
            "INSERT INTO tasks (id,title,status,type,favorito,em_preparacao) "
            "VALUES ('a','A','in_progress','dev',1,1)"
        )
        conn.execute("INSERT INTO tasks (id,title,status,type) VALUES ('b','B','pending','human')")
        conn.execute("INSERT INTO subtasks (id,task_id,text,type) VALUES ('sa','a','hi','dev')")
    conn.commit()
    conn.close()


def test_v10_drops_type_and_preserves_data(tmp_path):
    db_path = tmp_path / "tasks.db"
    _build_v9_db(db_path)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    _apply_migration_v10(conn, db_path)

    cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    assert "type" not in cols
    rows = {r["id"]: r for r in conn.execute("SELECT id, title, favorito, em_preparacao FROM tasks ORDER BY id")}
    assert set(rows) == {"a", "b"}
    assert rows["a"]["favorito"] == 1
    assert rows["a"]["em_preparacao"] == 1
    # subtask (e seu type) preservada
    sub = conn.execute("SELECT id, type FROM subtasks WHERE id='sa'").fetchone()
    assert sub["type"] == "dev"
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 10
    # indices recriados
    idx = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='tasks'"
        " AND name NOT LIKE 'sqlite_autoindex_%'"
    )}
    assert idx == {"idx_status", "idx_completed_at", "idx_hidden_at"}
    conn.close()


def test_v10_creates_backup(tmp_path):
    db_path = tmp_path / "tasks.db"
    _build_v9_db(db_path)
    conn = sqlite3.connect(str(db_path))
    _apply_migration_v10(conn, db_path)
    conn.close()
    backups = list(tmp_path.glob("tasks.db.bak-v9-*"))
    assert len(backups) == 1 and backups[0].stat().st_size > 0


def test_v10_is_idempotent(tmp_path):
    db_path = tmp_path / "tasks.db"
    _build_v9_db(db_path)
    conn = sqlite3.connect(str(db_path))
    _apply_migration_v10(conn, db_path)
    _apply_migration_v10(conn, db_path)  # no-op
    versions = [r[0] for r in conn.execute("SELECT version FROM _schema_version")]
    conn.close()
    assert versions.count(10) == 1
    # segundo run nao gera novo backup
    assert len(list(tmp_path.glob("tasks.db.bak-v9-*"))) == 1


def test_v10_reentrant_when_type_already_absent(tmp_path):
    db_path = tmp_path / "tasks.db"
    _build_v9_db(db_path, seed=False)
    conn = sqlite3.connect(str(db_path))
    # remove a coluna type previamente (banco divergente) sem registrar v10
    conn.executescript(
        "PRAGMA foreign_keys=OFF;"
        "CREATE TABLE t2 (id TEXT PRIMARY KEY, title TEXT NOT NULL,"
        " status TEXT NOT NULL CHECK (status IN ('pending','in_progress','done')),"
        " deps TEXT DEFAULT '', notes TEXT DEFAULT '', order_index INTEGER DEFAULT 0,"
        " created_at TIMESTAMP, completed_at TIMESTAMP, hidden_at TIMESTAMP,"
        " favorito INTEGER NOT NULL DEFAULT 0, permanente INTEGER NOT NULL DEFAULT 0,"
        " updated_at TEXT, em_preparacao INTEGER NOT NULL DEFAULT 0);"
        "DROP TABLE tasks; ALTER TABLE t2 RENAME TO tasks; PRAGMA foreign_keys=ON;"
    )
    conn.commit()
    _apply_migration_v10(conn, db_path)  # so registra a versao
    assert 10 in {r[0] for r in conn.execute("SELECT version FROM _schema_version")}
    conn.close()


def test_v10_aborts_atomically_under_concurrent_write_lock(tmp_path):
    db_path = tmp_path / "tasks.db"
    _build_v9_db(db_path)

    # Conexao concorrente segura um write lock -> BEGIN IMMEDIATE da v10 falha.
    writer = sqlite3.connect(str(db_path))
    writer.execute("BEGIN IMMEDIATE")
    writer.execute("INSERT INTO tasks (id,title,status,type) VALUES ('w','W','pending','agent')")

    victim = sqlite3.connect(str(db_path), timeout=0.2)
    with pytest.raises(MigrationError):
        _apply_migration_v10(victim, db_path)

    # Abort atomico: a coluna type ainda existe e v10 nao foi registrada.
    cols = {row[1] for row in victim.execute("PRAGMA table_info(tasks)")}
    assert "type" in cols
    assert 10 not in {r[0] for r in victim.execute("SELECT version FROM _schema_version")}
    victim.close()
    writer.rollback()
    writer.close()


def test_get_connection_enables_foreign_keys_and_cascade_delete(tmp_path):
    db_path = tmp_path / "app.db"
    close_connection()
    try:
        conn = get_connection(db_path)
        run_migrations(conn, db_path)
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        repo = TaskRepository(conn, db_path=str(db_path))
        repo.create(Task(id="t1", title="A"))
        repo.create_subtask(Subtask(id="s1", task_id="t1", text="x"))
        repo.delete("t1")
        # FK ON + ON DELETE CASCADE -> nenhuma subtask orfa
        orphans = conn.execute("SELECT COUNT(*) FROM subtasks WHERE task_id='t1'").fetchone()[0]
        assert orphans == 0
    finally:
        close_connection()


def test_module_has_v10_constants():
    # guarda de regressao: a versao alvo e as constantes do rebuild existem
    assert dbmod._V10_VERSION == 10
    assert "tasks_v10" in dbmod._TASKS_V10_DDL
