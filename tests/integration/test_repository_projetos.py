"""Integration tests for TaskRepository projetos operations (US-009).

Cobre:
- list_projetos: retorna projetos distintos de tasks ativas, ordenados
- list_projetos exclui tasks ocultas (hidden_at IS NOT NULL)
- list_projetos reflete normalizacao de 'outros'
- exists(): retorna True/False conforme presença no banco
- list_active() vs list_trash() isolamento

Stack: pytest + sqlite3 em memória (sem mock de banco)
"""
from __future__ import annotations

import sqlite3

import pytest

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


def _task(id: str, projeto: str = "outros", title: str = "T",
          status: Status = Status.PENDING) -> Task:
    return Task(
        id=id, title=title, status=status,
        type=TaskType.ONLINE, projeto=projeto, deps=[],
    )


# ── list_projetos ─────────────────────────────────────────────────────────────


def test_list_projetos_returns_distinct_projetos(repo):
    """US-009: list_projetos retorna projetos únicos (distinct) de tasks ativas."""
    repo.create(_task("t1", projeto="systemforge"))
    repo.create(_task("t2", projeto="systemforge"))  # duplicata — deve aparecer uma só
    repo.create(_task("t3", projeto="cliente-x"))
    repo.create(_task("t4", projeto="outros"))

    projetos = repo.list_projetos()

    assert projetos.count("systemforge") == 1, "Projeto duplicado deve aparecer apenas uma vez"
    assert "systemforge" in projetos
    assert "cliente-x" in projetos
    assert "outros" in projetos


def test_list_projetos_is_sorted_case_insensitively(repo):
    """US-009: projetos retornados em ordem case-insensitive."""
    repo.create(_task("t1", projeto="Zeta"))
    repo.create(_task("t2", projeto="alpha"))
    repo.create(_task("t3", projeto="Beta"))

    projetos = repo.list_projetos()
    lower_projetos = [p.lower() for p in projetos]

    assert lower_projetos == sorted(lower_projetos), (
        "list_projetos deve retornar projetos em ordem alfabética case-insensitive"
    )


def test_list_projetos_excludes_hidden_tasks(repo):
    """US-009/AC-8: projetos de tasks ocultas NÃO aparecem em list_projetos."""
    repo.create(_task("t1", projeto="visivel"))
    repo.create(_task("t2", projeto="somente-lixeira"))

    repo.mark_hidden("t2")

    projetos = repo.list_projetos()

    assert "visivel" in projetos
    assert "somente-lixeira" not in projetos, (
        "Projeto de task oculta não deve aparecer em list_projetos"
    )


def test_list_projetos_empty_when_no_active_tasks(repo):
    """US-009: list_projetos retorna lista vazia quando não há tasks ativas."""
    projetos = repo.list_projetos()
    assert projetos == []


def test_list_projetos_updates_after_all_tasks_of_project_hidden(repo):
    """US-009/AC-8: quando última task de um projeto é oculta, projeto some de list_projetos."""
    repo.create(_task("t1", projeto="unico"))
    assert "unico" in repo.list_projetos()

    repo.mark_hidden("t1")

    assert "unico" not in repo.list_projetos(), (
        "Projeto deve desaparecer de list_projetos quando todas suas tasks são ocultas"
    )


def test_list_projetos_updates_after_restore(repo):
    """US-009: projeto volta em list_projetos após restaurar task da Lixeira."""
    repo.create(_task("t1", projeto="restauravel"))
    repo.mark_hidden("t1")
    assert "restauravel" not in repo.list_projetos()

    repo.restore("t1")

    assert "restauravel" in repo.list_projetos(), (
        "Projeto deve voltar a list_projetos após restauração da task"
    )


def test_list_projetos_reflects_projeto_normalization(repo):
    """US-001/US-009: projeto normalizado para 'outros' aparece em list_projetos."""
    task = _task("t1", projeto="outros")
    repo.create(task)

    projetos = repo.list_projetos()
    assert "outros" in projetos, "Projeto 'outros' (normalizado) deve aparecer em list_projetos"


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
