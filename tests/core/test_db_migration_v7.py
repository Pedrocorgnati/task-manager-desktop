# suite: integration | loop: 05-20-decisoes-favorito-permanente-task-manager | task: task-007
# covers: core/db.py — migracao hardened v6 -> v7 (favorito/permanente)
"""Testes de integracao da migracao de schema v6 -> v7.

Validam o upgrade sobre uma fixture de banco real em v6: criacao das
colunas favorito/permanente, backup obrigatorio .bak-v6-<timestamp>,
leitura das tasks antigas, gate pos-migracao e abort sem retry em loop.
"""

import json
import logging
import sqlite3

import pytest

from task_manager_desktop.core.db import (
    _MIGRATIONS,
    _apply_migration_v7,
    run_migrations,
)
from task_manager_desktop.core.exceptions import MigrationError


def _build_v6_db(path, seed_tasks=()):
    """Constroi um banco real no path com schema exatamente em v6.

    Reproduz as migrations v1..v6 declarativas e registra cada versao em
    _schema_version, simulando um banco de uma versao anterior do app.
    """
    conn = sqlite3.connect(str(path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS _schema_version "
        "(version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    for version, ddl in _MIGRATIONS:
        conn.executescript(ddl)
        conn.execute("INSERT INTO _schema_version (version) VALUES (?)", (version,))
    for task_id, title in seed_tasks:
        conn.execute(
            "INSERT INTO tasks (id, title, status) VALUES (?, ?, 'pending')",
            (task_id, title),
        )
    conn.commit()
    conn.close()


def test_v7_adds_favorito_permanente_columns(tmp_path):
    """As colunas favorito/permanente sao INTEGER NOT NULL DEFAULT 0."""
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path)

    conn = sqlite3.connect(str(db_path))
    run_migrations(conn, db_path)

    # PRAGMA table_info -> (cid, name, type, notnull, dflt_value, pk)
    info = {row[1]: row for row in conn.execute("PRAGMA table_info(tasks)")}
    conn.close()

    for column in ("favorito", "permanente"):
        assert column in info, f"coluna {column} ausente apos migracao v7"
        assert str(info[column][2]).upper() == "INTEGER"
        assert info[column][3] == 1, f"{column} deveria ser NOT NULL"
        assert str(info[column][4]) == "0", f"{column} deveria ter DEFAULT 0"


def test_v7_creates_backup_file(tmp_path):
    """A migracao gera o backup obrigatorio .bak-v6-<timestamp>."""
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path)

    conn = sqlite3.connect(str(db_path))
    run_migrations(conn, db_path)
    conn.close()

    backups = list(tmp_path.glob("tasks.db.bak-v6-*"))
    assert len(backups) == 1, f"esperado 1 backup, encontrado {backups}"
    assert backups[0].stat().st_size > 0


def test_v7_preserves_old_tasks(tmp_path):
    """Tasks criadas em v6 continuam legiveis e recebem defaults 0."""
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path, seed_tasks=[("t-1", "Antiga 1"), ("t-2", "Antiga 2")])

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    run_migrations(conn, db_path)

    rows = {
        row["id"]: row
        for row in conn.execute(
            "SELECT id, title, favorito, permanente FROM tasks ORDER BY id"
        )
    }
    conn.close()

    assert set(rows) == {"t-1", "t-2"}
    assert rows["t-1"]["title"] == "Antiga 1"
    for row in rows.values():
        assert row["favorito"] == 0
        assert row["permanente"] == 0


def test_v7_bumps_schema_version(tmp_path):
    """Apos o gate, _schema_version registra a versao 7."""
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path)

    conn = sqlite3.connect(str(db_path))
    run_migrations(conn, db_path)
    versions = {row[0] for row in conn.execute("SELECT version FROM _schema_version")}
    conn.close()

    assert 7 in versions
    # run_migrations tambem aplica v8 (em_preparacao), v9 (type em subtasks), v10
    # (drop de tasks.type), v11 (workspace_root) e v12 (coin/dot) logo apos a v7.
    assert versions == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}


def test_v7_bumps_pragma_user_version(tmp_path):
    """Apos o gate, PRAGMA user_version retorna exatamente 7 (AC-1).

    O bump do contador nativo do SQLite e obrigatorio (criterio de
    rejeicao 6.8: migracao v7 sem PRAGMA user_version=7 ao final BLOQUEIA
    merge). Verifica tambem que a tabela _schema_version recebeu a versao
    no mesmo commit — as duas fontes devem ficar coerentes em 7.
    """
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path)

    conn = sqlite3.connect(str(db_path))
    run_migrations(conn, db_path)
    user_version = conn.execute("PRAGMA user_version").fetchone()[0]
    versions = {row[0] for row in conn.execute("SELECT version FROM _schema_version")}
    conn.close()

    # run_migrations encadeia a v8/v9/v10/v11/v12 apos a v7, entao o contador
    # nativo termina em 12; o essencial aqui e que o bump aconteceu (>= 7) e que
    # a v7 consta.
    assert user_version == 12, f"PRAGMA user_version deveria ser 12, retornou {user_version}"
    assert 7 in versions


def test_v7_is_idempotent(tmp_path):
    """Reexecutar a migracao nao duplica versao nem cria novo backup."""
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path)

    conn = sqlite3.connect(str(db_path))
    run_migrations(conn, db_path)
    run_migrations(conn, db_path)
    count = conn.execute("SELECT COUNT(*) FROM _schema_version").fetchone()[0]
    conn.close()

    assert count == 12
    backups = list(tmp_path.glob("tasks.db.bak-v6-*"))
    assert len(backups) == 1, "segunda execucao nao deve gerar novo backup"


def test_v7_reentrant_when_column_already_exists(tmp_path):
    """ALTER condicional: coluna pre-existente correta nao quebra a migracao."""
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path)

    pre = sqlite3.connect(str(db_path))
    pre.execute("ALTER TABLE tasks ADD COLUMN favorito INTEGER NOT NULL DEFAULT 0")
    pre.commit()
    pre.close()

    conn = sqlite3.connect(str(db_path))
    run_migrations(conn, db_path)
    info = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    versions = {row[0] for row in conn.execute("SELECT version FROM _schema_version")}
    conn.close()

    assert {"favorito", "permanente"} <= info
    assert 7 in versions


def test_v7_gate_fails_on_wrong_column_type(tmp_path):
    """Gate pos-migracao falha e reverte se a coluna v7 tem tipo errado."""
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path)

    pre = sqlite3.connect(str(db_path))
    # favorito pre-existente com tipo errado (TEXT em vez de INTEGER).
    pre.execute("ALTER TABLE tasks ADD COLUMN favorito TEXT")
    pre.commit()
    pre.close()

    conn = sqlite3.connect(str(db_path))
    with pytest.raises(MigrationError, match="gate v7 falhou"):
        run_migrations(conn, db_path)

    # ROLLBACK: versao 7 nao registrada, permanente nao persistido.
    versions = {row[0] for row in conn.execute("SELECT version FROM _schema_version")}
    info = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    conn.close()

    assert 7 not in versions
    assert "permanente" not in info


def test_v7_aborts_when_another_connection_writing(tmp_path):
    """BEGIN IMMEDIATE detecta outra conexao escrevendo e aborta a migracao."""
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path)

    writer = sqlite3.connect(str(db_path))
    writer.execute("BEGIN IMMEDIATE")
    writer.execute("INSERT INTO tasks (id, title, status) VALUES ('w', 'W', 'pending')")
    try:
        conn = sqlite3.connect(str(db_path), timeout=0.3)
        with pytest.raises(MigrationError, match="outra conexao"):
            run_migrations(conn, db_path)
        versions = {row[0] for row in conn.execute("SELECT version FROM _schema_version")}
        conn.close()
        assert 7 not in versions
    finally:
        writer.rollback()
        writer.close()


def test_v7_backup_skipped_for_in_memory_db():
    """Banco em memoria (db_path None) migra sem tentar backup."""
    conn = sqlite3.connect(":memory:")
    run_migrations(conn, None)
    versions = {row[0] for row in conn.execute("SELECT version FROM _schema_version")}
    info = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    conn.close()

    assert 7 in versions
    assert {"favorito", "permanente"} <= info


def test_v7_adds_updated_at_column(tmp_path):
    """A migracao v7 adiciona a coluna updated_at (TEXT NULL) em tasks (§3.4)."""
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path)

    conn = sqlite3.connect(str(db_path))
    run_migrations(conn, db_path)
    info = {row[1]: row for row in conn.execute("PRAGMA table_info(tasks)")}
    conn.close()

    assert "updated_at" in info, "coluna updated_at ausente apos migracao v7"
    # TEXT NULL sem default: linhas pre-v7 nunca foram tocadas.
    assert str(info["updated_at"][2]).upper() == "TEXT"
    assert info["updated_at"][3] == 0, "updated_at deveria aceitar NULL"


def test_v7_bool_columns_reject_out_of_domain_values(tmp_path):
    """O CHECK (... IN (0,1)) blinda favorito/permanente contra valores invalidos."""
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path)

    conn = sqlite3.connect(str(db_path))
    run_migrations(conn, db_path)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO tasks (id, title, status, favorito) "
            "VALUES ('bad', 'Bad', 'pending', 2)"
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO tasks (id, title, status, permanente) "
            "VALUES ('bad2', 'Bad2', 'pending', 5)"
        )
    conn.close()


def test_v7_precheck_aborts_when_already_migrated(tmp_path):
    """Precheck aborta se PRAGMA user_version ja indica >= 7 (banco migrado)."""
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path)

    # Simula um banco ja em v7: bump do contador nativo sem rodar a migracao.
    tamper = sqlite3.connect(str(db_path))
    tamper.execute("PRAGMA user_version = 7")
    tamper.commit()
    tamper.close()

    conn = sqlite3.connect(str(db_path))
    with pytest.raises(MigrationError, match="ja esta em v7"):
        run_migrations(conn, db_path)
    conn.close()


def test_v7_precheck_aborts_when_schema_version_not_six(tmp_path):
    """O precheck do v7 aborta se _schema_version nao estiver completa em v6.

    Exercita _apply_migration_v7 diretamente sobre um banco cuja tabela
    _schema_version registra apenas 1..5. O precheck de versao deve detectar
    a versao 6 ausente e abortar com erro explicito antes de qualquer ALTER.
    """
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path)

    # Tabela de controle indicando que v6 nunca foi aplicada.
    tamper = sqlite3.connect(str(db_path))
    tamper.execute("DELETE FROM _schema_version WHERE version = 6")
    tamper.commit()
    tamper.close()

    conn = sqlite3.connect(str(db_path))
    with pytest.raises(MigrationError, match="versoes anteriores ausentes"):
        _apply_migration_v7(conn, db_path)
    conn.close()


def test_v7_precheck_aborts_on_inconsistent_version_sources(tmp_path):
    """Precheck aborta na combinacao impossivel user_version 1..6 + tabela em 6.

    Um banco pre-v7 LEGITIMO tem user_version=0 (v1..v6 nunca tocam o
    contador nativo). Qualquer valor 1..6 e divergencia exotica.
    """
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path)

    tamper = sqlite3.connect(str(db_path))
    tamper.execute("PRAGMA user_version = 3")  # impossivel pelo fluxo canonico
    tamper.commit()
    tamper.close()

    conn = sqlite3.connect(str(db_path))
    with pytest.raises(MigrationError, match="estado inconsistente"):
        run_migrations(conn, db_path)
    conn.close()


def test_v7_legitimate_pre_v7_db_has_user_version_zero(tmp_path):
    """Um banco v6 legitimo (user_version=0, _schema_version=6) NAO e falso-positivo.

    As migracoes v1..v6 nunca tocam PRAGMA user_version; o precheck deve
    aceitar esse combo e migrar normalmente ate v7.
    """
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path)

    pre = sqlite3.connect(str(db_path))
    assert pre.execute("PRAGMA user_version").fetchone()[0] == 0
    pre.close()

    conn = sqlite3.connect(str(db_path))
    run_migrations(conn, db_path)  # nao deve levantar
    user_version = conn.execute("PRAGMA user_version").fetchone()[0]
    conn.close()
    # run_migrations encadeia a v8/v9/v10/v11/v12, entao o contador termina em 12.
    assert user_version == 12


def test_v7_aborts_on_pre_migration_corruption(tmp_path):
    """Banco corrompido aborta com erro explicito de corrupcao, nao erro de DDL."""
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path)

    # Corrompe o arquivo sobrescrevendo o miolo das paginas com lixo,
    # preservando o header magico para o sqlite ainda abrir a conexao.
    raw = db_path.read_bytes()
    corrupted = raw[:100] + b"\xff" * max(len(raw) - 100, 0)
    db_path.write_bytes(corrupted)

    conn = sqlite3.connect(str(db_path))
    with pytest.raises(MigrationError, match="corrompido"):
        run_migrations(conn, db_path)
    conn.close()


def test_v7_emits_structured_success_log(tmp_path, caplog):
    """O caminho de sucesso emite a linha estruturada migration.v6_to_v7 (§9)."""
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path)

    conn = sqlite3.connect(str(db_path))
    with caplog.at_level(logging.INFO, logger="task_manager_desktop.core.db"):
        run_migrations(conn, db_path)
    conn.close()

    structured = [
        rec.getMessage()
        for rec in caplog.records
        if "migration.v6_to_v7" in rec.getMessage() and "{" in rec.getMessage()
    ]
    assert structured, "linha estruturada migration.v6_to_v7 ausente no log"
    payload = json.loads(structured[-1].split("migration.v6_to_v7 ", 1)[1])
    for field in ("started_at", "finished_at", "duration_ms", "backup_path", "gate_result"):
        assert field in payload, f"campo §9 '{field}' ausente no log estruturado"
    assert payload["gate_result"] == "ok"
    assert payload["backup_path"] is not None


def test_v7_emits_structured_abort_log(tmp_path, caplog):
    """O caminho de abort tambem emite a linha estruturada migration.v6_to_v7 (§9)."""
    db_path = tmp_path / "tasks.db"
    _build_v6_db(db_path)

    tamper = sqlite3.connect(str(db_path))
    tamper.execute("PRAGMA user_version = 9")  # forca abort no precheck
    tamper.commit()
    tamper.close()

    conn = sqlite3.connect(str(db_path))
    with caplog.at_level(logging.ERROR, logger="task_manager_desktop.core.db"):
        with pytest.raises(MigrationError):
            run_migrations(conn, db_path)
    conn.close()

    structured = [
        rec.getMessage()
        for rec in caplog.records
        if "migration.v6_to_v7" in rec.getMessage() and "{" in rec.getMessage()
    ]
    assert structured, "linha estruturada de abort ausente no log"
    payload = json.loads(structured[-1].split("migration.v6_to_v7 ", 1)[1])
    for field in ("started_at", "finished_at", "duration_ms", "backup_path", "gate_result"):
        assert field in payload, f"campo §9 '{field}' ausente no log de abort"
    assert payload["gate_result"] == "aborted"
