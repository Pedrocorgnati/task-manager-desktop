# @tdd-unlocked: migracao v7 da feature favorito/permanente (source.md §3.3)
#   adicionou colunas favorito/permanente/updated_at e uma 7a versao de schema.
# Suite: unit | Module: module-0-foundations | Task: TASK-1
# TIDs: TID-0-1-001, TID-0-1-002, TID-0-1-003, TID-0-1-004, TID-0-1-005, TID-0-1-006, TID-0-1-007
import sqlite3

import pytest

from task_manager_desktop.core.db import run_migrations


@pytest.fixture
def mem():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


class TestSchemaV1Tabela:
    """TID-0-1-001 | covers: TASK-1/ST002 BDD#1 | suite: unit"""

    def test_schema_pos_migracoes_tabela_tasks_com_13_colunas(self, mem):
        run_migrations(mem)
        cols = {row[1] for row in mem.execute("PRAGMA table_info(tasks)")}
        expected = {
            "id", "title", "status", "deps", "notes",
            "order_index", "created_at", "completed_at", "hidden_at",
            "favorito", "permanente", "updated_at",
            # v8: flag manual do setor "Em preparação"
            "em_preparacao",
            # v10 dropou a coluna `type` (o tipo migrou para as subtasks).
        }
        assert cols == expected


class TestSchemaV1Indices:
    """TID-0-1-002 | covers: TASK-1/ST002 BDD#1 | suite: unit"""

    def test_schema_v1_cria_3_indices_canonicos(self, mem):
        run_migrations(mem)
        indices = {
            row[0] for row in mem.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='tasks'"
                " AND name NOT LIKE 'sqlite_autoindex_%'"
            )
        }
        assert indices == {"idx_status", "idx_completed_at", "idx_hidden_at"}


class TestSchemaVersionRow:
    """TID-0-1-003 | covers: TASK-1/ST002 BDD#1 | suite: unit"""

    def test_schema_version_recebe_row_version1_applied_at_nao_nulo(self, mem):
        run_migrations(mem)
        row = mem.execute("SELECT version, applied_at FROM _schema_version").fetchone()
        assert row is not None
        assert row["version"] == 1
        assert row["applied_at"] is not None


class TestRunMigracoesIdempotente:
    """TID-0-1-004 | covers: TASK-1/ST002 BDD#2 | suite: unit | classification: EDGE"""

    def test_run_migrations_em_banco_v1_e_idempotente(self, mem):
        run_migrations(mem)
        run_migrations(mem)
        count = mem.execute("SELECT COUNT(*) FROM _schema_version").fetchone()[0]
        # v10: drop da coluna `type` de tasks.
        assert count == 10


class TestCheckConstraintStatus:
    """TID-0-1-005 | covers: TASK-1/ST002 BDD#3 | suite: unit | classification: ERROR"""

    def test_check_constraint_status_rejeita_valor_invalido(self, mem):
        run_migrations(mem)
        with pytest.raises(sqlite3.IntegrityError):
            mem.execute("INSERT INTO tasks (id, title, status) VALUES ('x', 'T', 'invalido')")


class TestCheckConstraintType:
    """TID-0-1-006 | covers: TASK-1/ST002 BDD#4 | suite: unit | classification: ERROR"""

    def test_check_constraint_type_rejeita_valor_invalido(self, mem):
        # A coluna tasks.type (e seu CHECK) foi removida na migration v10;
        # inserir nela agora falha por coluna inexistente.
        run_migrations(mem)
        with pytest.raises(sqlite3.OperationalError):
            mem.execute(
                "INSERT INTO tasks (id, title, status, type) VALUES ('x', 'T', 'pending', 'invalido')"
            )


class TestInsertDefaults:
    """TID-0-1-007 | covers: TASK-1/ST002 BDD#5 | suite: unit"""

    def test_tasks_nao_tem_mais_coluna_type(self, mem):
        # O tipo deixou de ser atributo da task (migration v10): a coluna `type`
        # nao existe mais em tasks.
        run_migrations(mem)
        cols = {row[1] for row in mem.execute("PRAGMA table_info(tasks)")}
        assert "type" not in cols
