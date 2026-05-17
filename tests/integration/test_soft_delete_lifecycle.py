"""Integration tests for soft-delete lifecycle (US-011, US-012, US-016).

Cobre:
- US-011: mark_hidden, restore, list_trash, soft-delete automático após 3 dias,
          purga hard-delete após 30 dias, Lixeira vazia
- US-012: hard-delete permanente (contraste com soft-delete)
- US-016: falha de I/O na operação de cleanup não bloqueia o app

Stack: pytest + sqlite3 em memória (sem mock de banco)
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from task_manager_desktop.core.cleanup import (
    HARD_DELETE_DAYS,
    SOFT_DELETE_DAYS,
    run_cleanup_on_boot,
)
from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository

# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    run_migrations(c)
    yield c
    c.close()


@pytest.fixture
def repo(conn, tmp_path):
    return TaskRepository(conn, db_path=str(tmp_path / "tasks.db"))


def _task(id: str, title: str = "T", status: Status = Status.PENDING,
          completed_at: str | None = None) -> Task:
    return Task(
        id=id, title=title, status=status,
        type=TaskType.ONLINE, projeto="outros", deps=[],
        completed_at=completed_at,
    )


def _iso_ago(days: int) -> str:
    """Retorna ISO timestamp de N dias atrás."""
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.isoformat()


# ── mark_hidden / restore ──────────────────────────────────────────────────────


def test_mark_hidden_removes_task_from_list_active(repo):
    """US-011/AC-1: task marcada como oculta desaparece de list_active."""
    task = _task("t1", "Task 1", status=Status.DONE)
    repo.create(task)

    repo.mark_hidden("t1")

    active = repo.list_active()
    assert not any(t.id == "t1" for t in active), (
        "Task hidden não deve aparecer em list_active"
    )


def test_mark_hidden_task_appears_in_list_trash(repo):
    """US-011/AC-2: task oculta aparece em list_trash."""
    task = _task("t1", status=Status.DONE)
    repo.create(task)

    repo.mark_hidden("t1")

    trash = repo.list_trash()
    assert any(t.id == "t1" for t in trash), (
        "Task oculta deve aparecer na Lixeira"
    )
    assert trash[0].hidden_at is not None


def test_restore_brings_task_back_to_active(repo):
    """US-011/AC-2: restaurar task da Lixeira → volta para list_active."""
    task = _task("t1", status=Status.DONE)
    repo.create(task)
    repo.mark_hidden("t1")

    repo.restore("t1")

    active = repo.list_active()
    assert any(t.id == "t1" for t in active), (
        "Task restaurada deve aparecer em list_active"
    )
    trash = repo.list_trash()
    assert not any(t.id == "t1" for t in trash), (
        "Task restaurada não deve mais estar na Lixeira"
    )


def test_restore_clears_hidden_at_field(repo):
    """US-011: restore limpa hidden_at no banco."""
    task = _task("t1", status=Status.DONE)
    repo.create(task)
    repo.mark_hidden("t1")

    repo.restore("t1")

    restored = repo.get_by_id("t1")
    assert restored is not None
    assert restored.hidden_at is None, "hidden_at deve ser NULL após restore"


def test_trash_empty_when_no_hidden_tasks(repo):
    """US-011/AC-5: Lixeira vazia quando não há tasks ocultas."""
    task = _task("t1", status=Status.DONE)
    repo.create(task)
    # Não ocultar — lista_trash deve estar vazia

    trash = repo.list_trash()
    assert trash == [], "list_trash deve retornar lista vazia quando não há tasks ocultas"


# ── cleanup automático (3 dias / 30 dias) ─────────────────────────────────────


def test_cleanup_soft_deletes_done_tasks_after_3_days(repo, conn):
    """US-011/AC-1: run_cleanup_on_boot oculta tasks done há mais de 3 dias."""
    old_completed = _iso_ago(SOFT_DELETE_DAYS + 1)  # mais de 3 dias atrás
    task = _task("t1", status=Status.DONE, completed_at=old_completed)
    repo.create(task)
    # Atualizar completed_at diretamente no banco (repo.update não expõe completed_at livre)
    conn.execute(
        "UPDATE tasks SET completed_at = ? WHERE id = ?",
        (old_completed, "t1")
    )
    conn.commit()

    run_cleanup_on_boot(conn)

    active = repo.list_active()
    assert not any(t.id == "t1" for t in active), (
        "Task done há mais de 3 dias deve ser oculta automaticamente"
    )
    trash = repo.list_trash()
    assert any(t.id == "t1" for t in trash), (
        "Task oculta deve aparecer na Lixeira"
    )


def test_cleanup_does_not_hide_done_tasks_within_3_days(repo, conn):
    """US-011: tasks done há menos de 3 dias permanecem visíveis."""
    recent_completed = _iso_ago(1)  # 1 dia atrás — dentro da janela
    task = _task("t1", status=Status.DONE, completed_at=recent_completed)
    repo.create(task)
    conn.execute(
        "UPDATE tasks SET completed_at = ? WHERE id = ?",
        (recent_completed, "t1")
    )
    conn.commit()

    run_cleanup_on_boot(conn)

    active = repo.list_active()
    assert any(t.id == "t1" for t in active), (
        "Task done há menos de 3 dias não deve ser oculta"
    )


def test_cleanup_hard_deletes_tasks_after_30_days(repo, conn):
    """US-011/AC-4: run_cleanup_on_boot apaga permanentemente tasks completed há >30 dias."""
    very_old_completed = _iso_ago(HARD_DELETE_DAYS + 1)  # mais de 30 dias atrás
    task = _task("t1", status=Status.DONE, completed_at=very_old_completed)
    repo.create(task)
    conn.execute(
        "UPDATE tasks SET completed_at = ?, hidden_at = ? WHERE id = ?",
        (very_old_completed, very_old_completed, "t1")
    )
    conn.commit()

    run_cleanup_on_boot(conn)

    # Deve ter sido hard-deleted: não existe em nenhuma lista
    assert repo.get_by_id("t1") is None, (
        "Task completed há mais de 30 dias deve ser removida permanentemente"
    )
    trash = repo.list_trash()
    assert not any(t.id == "t1" for t in trash), (
        "Task purgada não deve aparecer na Lixeira"
    )


def test_cleanup_preserves_active_and_in_progress_tasks(repo, conn):
    """US-011: tasks ativas e in_progress NÃO são afetadas pelo cleanup."""
    pending_task = _task("t1", title="Pendente", status=Status.PENDING)
    in_progress_task = _task("t2", title="Em andamento", status=Status.IN_PROGRESS)
    repo.create(pending_task)
    repo.create(in_progress_task)

    run_cleanup_on_boot(conn)

    active = repo.list_active()
    ids = [t.id for t in active]
    assert "t1" in ids, "Task pending não deve ser afetada pelo cleanup"
    assert "t2" in ids, "Task in_progress não deve ser afetada pelo cleanup"


def test_cleanup_io_error_does_not_crash_silently(conn):
    """US-016/AC-3: falha de cleanup lança OperationalError (app captura e continua)."""
    # Forçar erro corrompendo a conexão
    conn.close()
    with pytest.raises(Exception):
        run_cleanup_on_boot(conn)


# ── US-012: hard-delete não aparece na Lixeira ────────────────────────────────


def test_hard_delete_task_not_in_trash(repo):
    """US-012/AC-1: task excluída via delete() é permanente — não aparece na Lixeira."""
    task = _task("t1", status=Status.DONE)
    repo.create(task)

    repo.delete("t1")

    assert repo.get_by_id("t1") is None, "Hard-delete deve remover task definitivamente"
    trash = repo.list_trash()
    assert not any(t.id == "t1" for t in trash), (
        "Task hard-deleted não deve aparecer na Lixeira"
    )


def test_soft_delete_via_mark_hidden_is_recoverable(repo):
    """US-012/AC-2: task oculta via mark_hidden é recuperável; hard-delete não é."""
    # Soft-delete → recuperável
    soft = _task("soft1", status=Status.DONE)
    repo.create(soft)
    repo.mark_hidden("soft1")
    assert any(t.id == "soft1" for t in repo.list_trash()), (
        "Task soft-deleted deve estar na Lixeira"
    )

    # Hard-delete → não recuperável
    hard = _task("hard1", status=Status.DONE)
    repo.create(hard)
    repo.delete("hard1")
    assert not any(t.id == "hard1" for t in repo.list_trash()), (
        "Task hard-deleted não deve estar na Lixeira"
    )
    assert repo.get_by_id("hard1") is None
