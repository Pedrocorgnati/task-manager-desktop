# @tdd-locked: do not edit without /tdd:unlock
# Suite: unit | Module: module-0-foundations | Task: TASK-2
# TIDs: TID-0-2-012, TID-0-2-013, TID-0-2-014
import re
import secrets
import sqlite3

import pytest

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.id_gen import ALPHABET, MAX_ATTEMPTS, generate_id


@pytest.fixture
def mem():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    yield conn
    conn.close()


class TestGenerateIdBase36:
    """TID-0-2-012 | covers: TASK-2/ST003 BDD#1 | suite: unit"""

    def test_generate_id_retorna_string_base36_tamanho_3(self, mem):
        tid = generate_id(mem)
        assert len(tid) == 3
        assert re.fullmatch(r"[0-9a-z]{3}", tid), f"ID nao e base36: {tid!r}"


class TestGenerateIdColisaoRetry:
    """TID-0-2-013 | covers: TASK-2/ST003 BDD#2 | suite: unit | classification: EDGE"""

    def test_generate_id_colisao_simulada_re_tenta_ate_max_attempts(self, mem, monkeypatch):
        call_count = [0]
        fixed = "aaa"
        # Primeira chamada: insere "aaa" para simular colisao
        mem.execute(
            "INSERT INTO tasks (id, title, status) VALUES (?, 'T', 'pending')", (fixed,)
        )
        mem.commit()

        original_choice = secrets.choice

        def fake_choice(seq):
            call_count[0] += 1
            # Retorna sempre 'a' para gerar 'aaa' (colisao) nas primeiras vezes,
            # depois retorna caracteres que formam outro ID valido.
            if call_count[0] <= 3:
                return "a"
            return original_choice(seq)

        monkeypatch.setattr(secrets, "choice", fake_choice)
        import task_manager_desktop.core.id_gen as id_gen_mod
        monkeypatch.setattr(id_gen_mod, "secrets", secrets)

        result = generate_id(mem)
        assert result != fixed, "deve gerar ID diferente do colidente"
        assert len(result) == 3


class TestGenerateIdUsaSecretsChoice:
    """TID-0-2-014 | covers: TASK-2/ST003 regra canonica | suite: unit"""

    def test_generate_id_usa_secrets_choice(self):
        import inspect
        import task_manager_desktop.core.id_gen as id_gen_mod
        src = inspect.getsource(id_gen_mod)
        assert "secrets.choice" in src, "generate_id deve usar secrets.choice conforme spec"
