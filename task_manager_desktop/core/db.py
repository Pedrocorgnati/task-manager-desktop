from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .exceptions import MigrationError

_logger = logging.getLogger(__name__)

_connection: sqlite3.Connection | None = None

# Thread que criou a conexao singleton. SQLite (check_same_thread=True por
# default) ja levanta ProgrammingError em uso cross-thread, mas a mensagem e
# opaca. Capturamos a identidade da thread criadora para falhar com um erro
# explicito (ver _assert_owner_thread). NAO e um rearranjo para thread-local
# real — e apenas um guard de regressao.
_connection_thread_id: int | None = None
_connection_thread_name: str | None = None

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

# Versao alvo do schema. A migracao v7 vive fora de _MIGRATIONS por exigir
# backup do arquivo .db, transacao unica e gate pos-migracao (ver
# _apply_migration_v7). As migracoes v1..v6 sao DDL declarativa simples.
_TARGET_SCHEMA_VERSION = 7

# Colunas adicionadas pela migracao v7: (nome, declaracao SQL).
#
# favorito/permanente: INTEGER NOT NULL DEFAULT 0 -> linhas existentes recebem 0
# automaticamente. O CHECK (... IN (0,1)) blinda contra valores fora do dominio
# booleano (ex: bug de caller gravando 2). LIMITACAO DO SQLITE: um CHECK so pode
# ser anexado no momento do ADD COLUMN; o SQLite NAO permite retrofitar um CHECK
# numa coluna pre-existente sem reconstruir a tabela (CREATE novo + copy + DROP +
# RENAME). Por isso o CHECK e aplicado apenas no caminho fresh-add do ALTER
# condicional abaixo — se a coluna ja existe (ambiente divergente), ela e mantida
# como esta e o gate pos-migracao apenas valida tipo/notnull/default, nao o CHECK.
#
# updated_at: TEXT NULL (sem DEFAULT). source.md §3.4 manda update_favorito /
# update_permanente tocarem updated_at na mesma transacao; sem esta coluna o
# repositorio cai num fallback condicional (_has_updated_at). Adicionada aqui
# para que o touch seja sempre confiavel. NULL e aceito: linhas pre-v7 nunca
# foram tocadas, logo nao tem timestamp de modificacao.
_V7_COLUMNS: tuple[tuple[str, str], ...] = (
    ("favorito", "INTEGER NOT NULL DEFAULT 0 CHECK (favorito IN (0, 1))"),
    ("permanente", "INTEGER NOT NULL DEFAULT 0 CHECK (permanente IN (0, 1))"),
    ("updated_at", "TEXT"),
)

# Subconjunto de _V7_COLUMNS sujeito ao gate estrito INTEGER NOT NULL DEFAULT 0.
# updated_at fica fora porque e TEXT NULL sem default; o gate o trata a parte.
_V7_BOOL_COLUMNS: tuple[str, ...] = ("favorito", "permanente")


def _assert_owner_thread() -> None:
    """Aborta com erro explicito se a conexao singleton for usada de outra thread.

    A conexao SQLite e criada com check_same_thread=True (default), o que ja
    levanta sqlite3.ProgrammingError em uso cross-thread — mas com uma mensagem
    generica. Este guard transforma a regressao num erro acionavel, nomeando a
    thread criadora e a thread infratora. Nao e um rearranjo para thread-local.
    """
    if _connection_thread_id is None:
        return
    current = threading.current_thread()
    if current.ident != _connection_thread_id:
        raise RuntimeError(
            "Conexao SQLite acessada de thread diferente da criadora. "
            f"Criada por thread '{_connection_thread_name}' "
            f"(id={_connection_thread_id}); acesso atual de '{current.name}' "
            f"(id={current.ident}). A conexao singleton e single-thread "
            "(thread principal Qt); nao compartilhe entre threads."
        )


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Retorna a conexao singleton (thread principal Qt).

    A conexao e criada uma unica vez, na thread que chamar esta funcao primeiro
    (tipicamente a thread principal Qt). Chamadas subsequentes de outra thread
    abortam com RuntimeError explicito (ver _assert_owner_thread).
    """
    global _connection, _connection_thread_id, _connection_thread_name
    if _connection is None:
        if db_path is None:
            raise RuntimeError("get_connection() chamado antes de ensure_data_dir_and_db()")
        _connection = sqlite3.connect(str(db_path))
        _connection.row_factory = sqlite3.Row
        # SQLite default e foreign_keys=0 POR CONEXAO. Sem isto, o
        # `ON DELETE CASCADE` de subtasks/permanent_task_schedules nao dispara
        # num restart do app (banco ja migrado), e TaskRepository.delete() —
        # que so faz `DELETE FROM tasks` confiando no cascade — deixaria
        # subtasks orfas. Habilitar e idempotente e seguro (fora de transacao).
        _connection.execute("PRAGMA foreign_keys = ON")
        creator = threading.current_thread()
        _connection_thread_id = creator.ident
        _connection_thread_name = creator.name
    else:
        _assert_owner_thread()
    return _connection


def run_migrations(conn: sqlite3.Connection, db_path: Path | None = None) -> None:
    """Aplica migrations pendentes. Idempotente — seguro chamar multiplas vezes.

    Args:
        conn: conexao SQLite aberta.
        db_path: caminho do arquivo .db. Necessario para o backup obrigatorio
            da migracao v7; quando None (banco em memoria), o backup e
            dispensado.

    Raises:
        MigrationError: se o banco estiver corrompido (PRAGMA quick_check) ou
            se a migracao v7 falhar (precheck de versao, backup ou gate
            pos-migracao). A excecao aborta a inicializacao do app e NAO deve
            ser recapturada para retry em loop.
    """
    # Integridade ANTES de qualquer DDL (v1..v6 ou v7). Num banco corrompido,
    # deixar as migracoes prosseguirem faz a falha emergir como um erro de
    # SQL confuso; este gate produz um erro explicito de corrupcao.
    _quick_check_or_abort(conn)

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

    # v7: migracao hardened com backup obrigatorio + gate pos-migracao.
    if _TARGET_SCHEMA_VERSION not in applied:
        _apply_migration_v7(conn, db_path)

    # v8: coluna em_preparacao (setor manual "Em preparação"). DDL simples e
    # reentrante — roda sempre apos a v7 ja ter garantido o schema base.
    _apply_migration_v8(conn)

    # v9: coluna type em subtasks (mesmo enum agent/dev/human de tasks). DDL
    # simples e reentrante — roda sempre apos a v8.
    _apply_migration_v9(conn)

    # v10: dropa a coluna tasks.type (o tipo migrou de vez para as subtasks).
    # Rebuild de tabela porque a coluna tem CHECK inline (SQLite nao dropa
    # coluna usada em CHECK). Hardened (backup + transacao atomica), reentrante.
    _apply_migration_v10(conn, db_path)

    # v11: coluna workspace_root + seed das linhas existentes. DDL simples e
    # reentrante — roda sempre apos a v10.
    _apply_migration_v11(conn)

    # v12: colunas booleanas coin_favorite + dot_favorite (marcadores de
    # ranqueamento irmaos de favorito). DDL simples e reentrante — roda apos v11.
    _apply_migration_v12(conn)


# Versao da migracao v8 (coluna em_preparacao). Vive fora de _MIGRATIONS para
# nao interferir no precheck dual da v7 (que assume max(_schema_version) == 6
# num banco pre-v7); aplicada explicitamente apos a v7 em run_migrations.
_V8_VERSION = 8


def _apply_migration_v8(conn: sqlite3.Connection) -> None:
    """Migracao v7 -> v8: adiciona a coluna booleana em_preparacao a tasks.

    Idempotente e reentrante: nao reaplica se a versao 8 ja consta em
    _schema_version, e so emite o ALTER se a coluna ainda nao existe (banco
    divergente). INTEGER NOT NULL DEFAULT 0 -> linhas existentes recebem 0;
    o CHECK blinda contra valores fora do dominio booleano.
    """
    applied = {row[0] for row in conn.execute("SELECT version FROM _schema_version")}
    if _V8_VERSION in applied:
        return
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    if "em_preparacao" not in existing_cols:
        conn.execute(
            "ALTER TABLE tasks ADD COLUMN em_preparacao INTEGER NOT NULL "
            "DEFAULT 0 CHECK (em_preparacao IN (0, 1))"
        )
    conn.execute("INSERT INTO _schema_version (version) VALUES (?)", (_V8_VERSION,))
    conn.execute(f"PRAGMA user_version = {_V8_VERSION}")
    conn.commit()
    _logger.info("migracao v7->v8: coluna em_preparacao garantida em tasks")


# Versao da migracao v10 (drop da coluna tasks.type). Rebuild de tabela.
_V10_VERSION = 10

# DDL canonica da tabela `tasks` pos-v10 (sem a coluna `type`). Mantida como
# constante para o rebuild reconstruir com os mesmos CHECK/defaults das demais
# colunas (status/favorito/permanente/em_preparacao).
_TASKS_V10_DDL = """
CREATE TABLE tasks_v10 (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('pending', 'in_progress', 'done')),
    deps        TEXT DEFAULT '',
    notes       TEXT DEFAULT '',
    order_index INTEGER DEFAULT 0,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    hidden_at   TIMESTAMP NULL,
    favorito    INTEGER NOT NULL DEFAULT 0 CHECK (favorito IN (0, 1)),
    permanente  INTEGER NOT NULL DEFAULT 0 CHECK (permanente IN (0, 1)),
    updated_at  TEXT,
    em_preparacao INTEGER NOT NULL DEFAULT 0 CHECK (em_preparacao IN (0, 1))
)
"""

_TASKS_V10_COLUMNS = (
    "id, title, status, deps, notes, order_index, created_at, "
    "completed_at, hidden_at, favorito, permanente, updated_at, em_preparacao"
)


def _backup_before_v10(conn: sqlite3.Connection, db_path: Path | None) -> Path | None:
    """Backup obrigatorio antes do rebuild destrutivo da v10.

    O rebuild dropa a tabela `tasks`; um backup `.bak-v9-<ts>` da uma copia de
    seguranca para quem ja estava em v7/v8/v9 (e nao tem mais o `.bak-v6` da v7,
    ou cujos dados favorito/permanente/em_preparacao sao posteriores a ele).
    Retorna o path do backup, ou None se o banco e em memoria. Falha ao copiar
    levanta MigrationError (mesma disciplina da v7).
    """
    if db_path is None or not db_path.exists():
        _logger.info("migracao v9->v10: backup dispensado (banco em memoria)")
        return None
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.with_name(f"{db_path.name}.bak-v9-{timestamp}")
    try:
        shutil.copy2(db_path, backup_path)
    except OSError as exc:
        raise MigrationError(
            f"migracao v10 abortada: falha ao criar backup obrigatorio em "
            f"{backup_path}: {exc}. Crie manualmente uma copia de {db_path} "
            "antes de reabrir o app."
        ) from exc
    _logger.info("migracao v9->v10: backup criado em %s", backup_path)
    return backup_path


def _apply_migration_v10(conn: sqlite3.Connection, db_path: Path | None = None) -> None:
    """Migracao v9 -> v10: remove a coluna `type` da tabela `tasks`.

    O tipo (agent/dev/human) deixou de ser um atributo da task e passou a viver
    exclusivamente nas subtasks. Como `tasks.type` tem um CHECK inline, o SQLite
    nao permite `ALTER TABLE ... DROP COLUMN`; e necessario reconstruir a tabela.

    Rebuild HARDENED (rebuild destrutivo): backup obrigatorio, foreign_keys=OFF
    FORA da transacao (PRAGMA foreign_keys e no-op dentro de transacao), rebuild
    inteiro num unico BEGIN IMMEDIATE (atomico: um crash no meio nao deixa o
    banco sem a tabela `tasks`), gate de contagem de linhas (copiou todas) e bump
    de versao no MESMO commit; ROLLBACK em qualquer falha. Idempotente: nao
    reaplica se a versao 10 ja consta; reentrante: se a coluna ja sumiu (banco
    divergente) apenas registra a versao.
    """
    applied = {row[0] for row in conn.execute("SELECT version FROM _schema_version")}
    if _V10_VERSION in applied:
        return

    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    if "type" not in existing_cols:
        # Banco divergente: a coluna ja nao existe. So registra a versao.
        conn.execute("INSERT INTO _schema_version (version) VALUES (?)", (_V10_VERSION,))
        conn.execute(f"PRAGMA user_version = {_V10_VERSION}")
        conn.commit()
        _logger.info("migracao v9->v10: coluna type ja ausente; versao registrada")
        return

    # Backup obrigatorio antes de qualquer DROP.
    _backup_before_v10(conn, db_path)

    prev_isolation = conn.isolation_level
    # foreign_keys nao pode ser alterado dentro de uma transacao -> setar ANTES
    # do BEGIN. Com FK ON (get_connection), DROP TABLE tasks dispararia o
    # cascade e apagaria TODAS as subtasks; OFF durante o rebuild evita isso.
    conn.isolation_level = None
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        try:
            conn.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            raise MigrationError(
                "migracao v10 abortada: outra conexao esta escrevendo no banco "
                f"({exc}). Feche outras instancias do app e tente novamente."
            ) from exc
        try:
            conn.execute(_TASKS_V10_DDL)
            conn.execute(
                f"INSERT INTO tasks_v10 ({_TASKS_V10_COLUMNS}) "
                f"SELECT {_TASKS_V10_COLUMNS} FROM tasks"
            )
            src = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            dst = conn.execute("SELECT COUNT(*) FROM tasks_v10").fetchone()[0]
            if src != dst:
                raise MigrationError(
                    f"migracao v10 abortada: copia incompleta ({dst} de {src} "
                    "linhas). Rollback aplicado; nenhuma alteracao persistida."
                )
            conn.execute("DROP TABLE tasks")
            conn.execute("ALTER TABLE tasks_v10 RENAME TO tasks")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status       ON tasks(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_completed_at ON tasks(completed_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hidden_at    ON tasks(hidden_at)")
            conn.execute(
                "INSERT INTO _schema_version (version) VALUES (?)", (_V10_VERSION,)
            )
            conn.execute(f"PRAGMA user_version = {_V10_VERSION}")
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.isolation_level = prev_isolation
    _logger.info("migracao v9->v10: coluna type removida de tasks (rebuild atomico)")


# Versao da migracao v9 (coluna type em subtasks). Vive fora de _MIGRATIONS,
# como a v8, para nao interferir no precheck dual da v7. Aplicada apos a v8.
_V9_VERSION = 9


def _apply_migration_v9(conn: sqlite3.Connection) -> None:
    """Migracao v8 -> v9: adiciona a coluna `type` a subtasks.

    Idempotente e reentrante: nao reaplica se a versao 9 ja consta em
    _schema_version, e so emite o ALTER se a coluna ainda nao existe (banco
    divergente). TEXT NOT NULL DEFAULT 'agent' -> linhas existentes herdam
    'agent'; o CHECK blinda contra valores fora do dominio agent/dev/human.
    """
    applied = {row[0] for row in conn.execute("SELECT version FROM _schema_version")}
    if _V9_VERSION in applied:
        return
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(subtasks)")}
    if "type" not in existing_cols:
        # TEXT NOT NULL DEFAULT 'agent' -> linhas existentes herdam 'agent'; o
        # CHECK blinda contra valores fora do dominio agent/dev/human.
        conn.execute(
            "ALTER TABLE subtasks ADD COLUMN type TEXT NOT NULL "
            "DEFAULT 'agent' CHECK (type IN ('agent', 'dev', 'human'))"
        )
    conn.execute("INSERT INTO _schema_version (version) VALUES (?)", (_V9_VERSION,))
    conn.execute(f"PRAGMA user_version = {_V9_VERSION}")
    conn.commit()
    _logger.info("migracao v8->v9: coluna type garantida em subtasks")


# Versao da migracao v11 (coluna workspace_root). Vive fora de _MIGRATIONS,
# como v8/v9/v10, para nao interferir no precheck dual da v7. Aplicada apos v10.
_V11_VERSION = 11


def _apply_migration_v11(conn: sqlite3.Connection) -> None:
    """Migracao v10 -> v11: adiciona `workspace_root` a tasks + seed.

    `workspace_root` e o caminho do workspace do repositorio SystemForge
    associado a task (campo obrigatorio no formulario). Coluna TEXT NOT NULL
    DEFAULT '' -> linhas existentes recebem '' e, em seguida, as que ficarem
    vazias sao semeadas com 'output/workspace/{slug-do-titulo}' (ex.: a task
    'Lead Hunting Engine' recebe 'output/workspace/lead-hunting-engine').
    Idempotente e reentrante: nao reaplica se a versao 11 ja consta, e so emite
    o ALTER se a coluna ainda nao existe (banco divergente).
    """
    from task_manager_desktop.core.models import default_workspace_root

    applied = {row[0] for row in conn.execute("SELECT version FROM _schema_version")}
    if _V11_VERSION in applied:
        return
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    if "workspace_root" not in existing_cols:
        conn.execute(
            "ALTER TABLE tasks ADD COLUMN workspace_root TEXT NOT NULL DEFAULT ''"
        )
    # Seed deterministico: o slug nao e expressavel em SQL puro, entao computamos
    # em Python e atualizamos linha a linha as que estao sem workspace_root.
    rows = conn.execute(
        "SELECT id, title FROM tasks WHERE workspace_root IS NULL OR workspace_root = ''"
    ).fetchall()
    for row in rows:
        conn.execute(
            "UPDATE tasks SET workspace_root = ? WHERE id = ?",
            (default_workspace_root(row[1] or ""), row[0]),
        )
    conn.execute("INSERT INTO _schema_version (version) VALUES (?)", (_V11_VERSION,))
    conn.execute(f"PRAGMA user_version = {_V11_VERSION}")
    conn.commit()
    _logger.info(
        "migracao v10->v11: coluna workspace_root garantida + seed em %d linhas",
        len(rows),
    )


# Versao da migracao v12 (colunas coin_favorite + dot_favorite). Vive fora de
# _MIGRATIONS, como v8..v11, para nao interferir no precheck dual da v7.
_V12_VERSION = 12

# Colunas booleanas da v12: mesmo contrato de favorito/permanente/em_preparacao
# (INTEGER NOT NULL DEFAULT 0 + CHECK IN (0,1) -> linhas existentes recebem 0).
_V12_COLUMNS: tuple[str, ...] = ("coin_favorite", "dot_favorite")


def _apply_migration_v12(conn: sqlite3.Connection) -> None:
    """Migracao v11 -> v12: adiciona coin_favorite e dot_favorite a tasks.

    Sao marcadores de ranqueamento irmaos de `favorito` (a moeda e a bolinha do
    card), agora persistidos em vez de viverem apenas em memoria. Idempotente e
    reentrante: nao reaplica se a versao 12 ja consta em _schema_version, e so
    emite cada ALTER se a coluna ainda nao existe (banco divergente). INTEGER
    NOT NULL DEFAULT 0 -> linhas existentes recebem 0; o CHECK blinda contra
    valores fora do dominio booleano.
    """
    applied = {row[0] for row in conn.execute("SELECT version FROM _schema_version")}
    if _V12_VERSION in applied:
        return
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    for column in _V12_COLUMNS:
        if column not in existing_cols:
            conn.execute(
                f"ALTER TABLE tasks ADD COLUMN {column} INTEGER NOT NULL "
                f"DEFAULT 0 CHECK ({column} IN (0, 1))"
            )
    conn.execute("INSERT INTO _schema_version (version) VALUES (?)", (_V12_VERSION,))
    conn.execute(f"PRAGMA user_version = {_V12_VERSION}")
    conn.commit()
    _logger.info(
        "migracao v11->v12: colunas coin_favorite + dot_favorite garantidas em tasks"
    )


def _backup_before_v7(conn: sqlite3.Connection, db_path: Path | None) -> Path | None:
    """Cria o backup obrigatorio .bak-v6-<timestamp> antes de qualquer ALTER.

    Retorna o path do backup criado, ou None quando o banco e em memoria
    (sem arquivo a copiar). Falha ao copiar levanta MigrationError.
    """
    if db_path is None or not db_path.exists():
        _logger.info("migracao v6->v7: backup dispensado (banco em memoria)")
        return None

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.with_name(f"{db_path.name}.bak-v6-{timestamp}")
    try:
        shutil.copy2(db_path, backup_path)
    except OSError as exc:
        raise MigrationError(
            f"migracao v7 abortada: falha ao criar backup obrigatorio em "
            f"{backup_path}: {exc}. Crie manualmente uma copia de {db_path} "
            "antes de reabrir o app."
        ) from exc
    _logger.info("migracao v6->v7: backup criado em %s", backup_path)
    return backup_path


def _gate_v7(conn: sqlite3.Connection, backup_path: Path | None) -> None:
    """Gate pos-migracao v7: confirma presenca e contrato de cada coluna v7.

    Para favorito/permanente exige INTEGER NOT NULL DEFAULT 0; para updated_at
    exige apenas presenca da coluna (TEXT NULL, sem default). Levanta
    MigrationError dentro da transacao (o chamador faz ROLLBACK) em qualquer
    desvio.
    """
    # PRAGMA table_info -> (cid, name, type, notnull, dflt_value, pk)
    info = {row[1]: row for row in conn.execute("PRAGMA table_info(tasks)")}
    hint = (
        f" Restaure o backup em {backup_path} para reverter."
        if backup_path is not None
        else ""
    )

    # 1. Presenca de TODAS as colunas v7 (booleanas + updated_at).
    for column, _decl in _V7_COLUMNS:
        if column not in info:
            raise MigrationError(
                f"gate v7 falhou: coluna '{column}' ausente apos ALTER.{hint}"
            )

    # 2. Contrato estrito das colunas booleanas: INTEGER NOT NULL DEFAULT 0.
    for column in _V7_BOOL_COLUMNS:
        row = info[column]
        col_type = str(row[2] or "").upper()
        notnull = row[3]
        default = row[4]
        if col_type != "INTEGER":
            raise MigrationError(
                f"gate v7 falhou: coluna '{column}' tem tipo '{col_type}', "
                f"esperado INTEGER.{hint}"
            )
        if notnull != 1:
            raise MigrationError(
                f"gate v7 falhou: coluna '{column}' nao e NOT NULL.{hint}"
            )
        if str(default) != "0":
            raise MigrationError(
                f"gate v7 falhou: coluna '{column}' tem DEFAULT '{default}', "
                f"esperado 0.{hint}"
            )


def _utc_now_iso() -> str:
    """Timestamp UTC ISO-8601 para os campos started_at/finished_at do log §9."""
    return datetime.now(timezone.utc).isoformat()


def _log_migration_event(level: int, **fields: object) -> None:
    """Emite a linha estruturada `migration.v6_to_v7` (observabilidade §9).

    Usa o idioma de logging ja presente em db.py (_logger). O payload vai como
    JSON num campo unico para ser parseavel sem ambiguidade — diferente do
    free-text anterior. Chamado tanto no caminho de sucesso quanto no de abort.
    """
    payload = json.dumps(fields, default=str, sort_keys=True, ensure_ascii=False)
    _logger.log(level, "migration.v6_to_v7 %s", payload)


def _quick_check_or_abort(conn: sqlite3.Connection) -> None:
    """Roda PRAGMA quick_check ANTES de qualquer backup/ALTER da v7.

    Num banco corrompido, deixar a migracao prosseguir faz a falha emergir como
    um erro de DDL/ALTER confuso. Detectar a corrupcao aqui produz um erro
    explicito "banco corrompido". quick_check e mais barato que integrity_check
    e suficiente como gate de pre-migracao.
    """
    try:
        row = conn.execute("PRAGMA quick_check").fetchone()
    except sqlite3.DatabaseError as exc:
        raise MigrationError(
            "migracao v7 abortada: banco de dados corrompido — PRAGMA "
            f"quick_check falhou ({exc}). Restaure um backup integro antes "
            "de reabrir o app."
        ) from exc
    result = row[0] if row else "error"
    if result != "ok":
        raise MigrationError(
            "migracao v7 abortada: banco de dados corrompido — PRAGMA "
            f"quick_check retornou '{result}'. Restaure um backup integro "
            "antes de reabrir o app."
        )


def _precheck_v7_version(conn: sqlite3.Connection) -> None:
    """Precheck de versao: le PRAGMA user_version E a tabela _schema_version.

    As migracoes v1..v6 bumpam SOMENTE a tabela _schema_version, nunca o
    PRAGMA user_version — portanto um banco pre-v7 LEGITIMO tem
    user_version=0 e _schema_version=6. Isso NAO e corrupcao e nao deve
    gerar falso-positivo. So o PRAGMA da migracao v7 grava user_version=7.

    Aborta apenas em estados genuinamente impossiveis:
      - _schema_version ausente das versoes v1..v6 (schema incompleto);
      - _schema_version corrente != 6;
      - user_version >= 7 (banco ja migrado — re-rodar v7 seria incoerente);
      - combinacao contraditoria entre as duas fontes (ex: user_version
        indica >= 7 mas a tabela nao tem a versao 7, ou vice-versa).
    """
    # Fonte A: tabela _schema_version (historico de migracoes aplicadas).
    applied = {row[0] for row in conn.execute("SELECT version FROM _schema_version")}
    missing = [version for version, _ddl in _MIGRATIONS if version not in applied]
    if missing:
        raise MigrationError(
            f"migracao v7 abortada: versoes anteriores ausentes {missing} na "
            "tabela _schema_version; o schema precisa estar em v6 antes do "
            "upgrade."
        )
    table_version = max(applied)

    # Fonte B: PRAGMA user_version (contador nativo do SQLite).
    user_version = conn.execute("PRAGMA user_version").fetchone()[0]

    # Estado: ja migrado. Detectavel por qualquer uma das fontes.
    if user_version >= _TARGET_SCHEMA_VERSION or table_version >= _TARGET_SCHEMA_VERSION:
        raise MigrationError(
            "migracao v7 abortada: banco ja esta em v7 ou superior "
            f"(PRAGMA user_version={user_version}, "
            f"_schema_version={table_version}). Nao re-execute a migracao."
        )

    # Estado: tabela nao esta exatamente em v6.
    if table_version != 6:
        raise MigrationError(
            "migracao v7 abortada: versao na tabela _schema_version e "
            f"{table_version}, esperado 6 (PRAGMA user_version={user_version})."
        )

    # Estado: combinacao contraditoria. Um banco pre-v7 legitimo tem
    # user_version == 0 (v1..v6 nunca tocam o contador nativo). Qualquer
    # outro valor 1..6 indica que algo escreveu user_version fora do fluxo
    # canonico — divergencia que exige analise manual, nao migracao cega.
    if user_version != 0:
        raise MigrationError(
            "migracao v7 abortada: estado inconsistente entre as duas fontes "
            f"de versao — PRAGMA user_version={user_version} mas "
            f"_schema_version={table_version}. Um banco pre-v7 legitimo tem "
            "user_version=0 (as migracoes v1..v6 nunca tocam o contador "
            "nativo). Este combo e impossivel pelo fluxo canonico; analise "
            "o banco manualmente antes de migrar."
        )


def _apply_migration_v7(conn: sqlite3.Connection, db_path: Path | None) -> None:
    """Migracao v6 -> v7: adiciona favorito, permanente e updated_at em tasks.

    Sequencia hardened: precheck de versao dual (PRAGMA user_version + tabela
    _schema_version), backup obrigatorio, transacao unica BEGIN IMMEDIATE,
    ALTER condicional (reentrante), gate pos-migracao e bump explicito apos o
    gate. Falha em qualquer etapa levanta MigrationError; a transacao e
    revertida via ROLLBACK e a inicializacao do app aborta sem retry em loop.
    Emite a linha estruturada `migration.v6_to_v7` (§9) tanto no sucesso
    quanto no abort.

    A verificacao de integridade (PRAGMA quick_check) acontece uma vez no
    inicio de run_migrations, antes de qualquer DDL — ver run_migrations.
    """
    started_at_mono = time.monotonic()
    started_at_iso = _utc_now_iso()
    backup_path: Path | None = None
    _logger.info("migracao v6->v7: inicio")

    try:
        # 1. Precheck de versao dual (user_version + _schema_version).
        _precheck_v7_version(conn)

        # 2. Backup obrigatorio antes de qualquer ALTER.
        backup_path = _backup_before_v7(conn, db_path)

        # 3. Precheck de schema: colunas ja existentes (migracao reentrante).
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}

        # 4. Transacao unica. BEGIN IMMEDIATE detecta outra conexao escrevendo.
        prev_isolation = conn.isolation_level
        conn.isolation_level = None
        try:
            try:
                conn.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as exc:
                raise MigrationError(
                    "migracao v7 abortada: outra conexao esta escrevendo no "
                    f"banco ({exc}). Feche outras instancias do app e tente "
                    "novamente."
                ) from exc

            try:
                # 5. ALTER condicional: apenas para colunas ausentes. O CHECK
                # de favorito/permanente so e aplicado neste fresh-add (o
                # SQLite nao retrofita CHECK em coluna pre-existente — ver
                # comentario em _V7_COLUMNS).
                for column, decl in _V7_COLUMNS:
                    if column not in existing_cols:
                        conn.execute(
                            f"ALTER TABLE tasks ADD COLUMN {column} {decl}"
                        )

                # 6. Gate pos-migracao (dentro da transacao).
                _gate_v7(conn, backup_path)

                # 7. Bump explicito apenas apos o gate passar. Registra a
                # versao nas DUAS fontes: a tabela _schema_version (historico
                # de migracoes aplicadas) e o PRAGMA user_version (contador
                # nativo do SQLite). Ambos no mesmo BEGIN IMMEDIATE/COMMIT —
                # PRAGMA user_version e transacional e commita junto.
                conn.execute(
                    "INSERT INTO _schema_version (version) VALUES (?)",
                    (_TARGET_SCHEMA_VERSION,),
                )
                conn.execute(f"PRAGMA user_version = {_TARGET_SCHEMA_VERSION}")
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        finally:
            conn.isolation_level = prev_isolation
    except MigrationError as exc:
        # Caminho de ABORT: emite a linha estruturada §9 antes de propagar.
        duration_ms = (time.monotonic() - started_at_mono) * 1000
        _log_migration_event(
            logging.ERROR,
            event="migration.v6_to_v7",
            started_at=started_at_iso,
            finished_at=_utc_now_iso(),
            duration_ms=round(duration_ms, 1),
            backup_path=str(backup_path) if backup_path is not None else None,
            gate_result="aborted",
            error=str(exc),
        )
        raise

    rows = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    duration_ms = (time.monotonic() - started_at_mono) * 1000
    # Caminho de SUCESSO: linha estruturada §9.
    _log_migration_event(
        logging.INFO,
        event="migration.v6_to_v7",
        started_at=started_at_iso,
        finished_at=_utc_now_iso(),
        duration_ms=round(duration_ms, 1),
        backup_path=str(backup_path) if backup_path is not None else None,
        gate_result="ok",
        rows_affected=rows,
    )
    _logger.info(
        "migracao v6->v7: fim — %d linhas em tasks, %.1f ms", rows, duration_ms
    )


def validate_database(conn: sqlite3.Connection) -> None:
    """Executa PRAGMA integrity_check. Levanta DatabaseError se banco estiver corrompido."""
    row = conn.execute("PRAGMA integrity_check").fetchone()
    result = row[0] if row else "error"
    if result != "ok":
        raise sqlite3.DatabaseError(f"integrity_check falhou: {result}")


def close_connection() -> None:
    """Fecha e limpa a conexao singleton (para uso em testes)."""
    global _connection, _connection_thread_id, _connection_thread_name
    if _connection is not None:
        _connection.close()
        _connection = None
    # Limpa a identidade da thread criadora para que um novo get_connection()
    # (ex: na proxima fixture de teste) possa recriar a conexao em qualquer
    # thread sem disparar o guard cross-thread.
    _connection_thread_id = None
    _connection_thread_name = None
