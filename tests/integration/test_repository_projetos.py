"""Integration tests for TaskRepository operations.

Cobre:
- exists(): retorna True/False conforme presença no banco
- list_active() vs list_trash() isolamento

Stack: pytest + sqlite3 em memória (sem mock de banco)
"""
from __future__ import annotations

import sqlite3

import pytest

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Status, Task
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


def _task(id: str, title: str = "T",
          status: Status = Status.PENDING) -> Task:
    return Task(
        id=id, title=title, status=status,
        deps=[],
    )


# ── exists() ──────────────────────────────────────────────────────────────────


def test_exists_returns_true_for_existing_task(repo):
    """exists() retorna True para task criada no banco."""
    task = _task("t1")
    repo.create(task)
    assert repo.exists("t1") is True


def test_exists_returns_false_for_nonexistent_task(repo):
    """exists() retorna False para ID inexistente."""
    assert repo.exists("nao-existe") is False


def test_exists_returns_true_for_hidden_task(repo):
    """exists() encontra task mesmo oculta (hidden_at != NULL)."""
    task = _task("t1")
    repo.create(task)
    repo.mark_hidden("t1")
    assert repo.exists("t1") is True, "exists() deve encontrar tasks ocultas também"


def test_exists_returns_false_after_hard_delete(repo):
    """exists() retorna False após hard-delete."""
    task = _task("t1")
    repo.create(task)
    repo.delete("t1")
    assert repo.exists("t1") is False


# ── isolamento list_active vs list_trash ──────────────────────────────────────


def test_list_active_does_not_contain_hidden_tasks(repo):
    """list_active exclui exclusivamente tasks com hidden_at preenchido."""
    repo.create(_task("a1", status=Status.PENDING))
    repo.create(_task("a2", status=Status.IN_PROGRESS))
    repo.create(_task("h1", status=Status.DONE))
    repo.mark_hidden("h1")

    active = repo.list_active()
    ids = [t.id for t in active]
    assert "a1" in ids
    assert "a2" in ids
    assert "h1" not in ids


def test_list_trash_contains_only_hidden_tasks(repo):
    """list_trash retorna apenas tasks com hidden_at preenchido."""
    repo.create(_task("active1"))
    repo.create(_task("hidden1", status=Status.DONE))
    repo.mark_hidden("hidden1")

    trash = repo.list_trash()
    ids = [t.id for t in trash]
    assert "hidden1" in ids
    assert "active1" not in ids
