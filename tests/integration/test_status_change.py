"""Integration tests for EditTaskController.handle_status_change (US-004 + US-005).

Cobre:
- US-004: mudar status via seletor no card → persiste, recalcula setor, completed_at
- US-005: promoção automática de dependentes diretos ao concluir uma task
- Cenário de erro I/O ao mudar status

Stack: pytest + sqlite3 em memória (sem mock de banco)
"""
from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from task_manager_desktop.controllers.edit_task_controller import EditTaskController
from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Sector, Status, Task, TaskType
from task_manager_desktop.core.sector import compute_sector, count_open_deps
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


@pytest.fixture
def mock_task_list():
    return MagicMock()


@pytest.fixture
def mock_main_window():
    return MagicMock()


@pytest.fixture
def ctrl(repo, mock_task_list, mock_main_window):
    return EditTaskController(repo, mock_task_list, mock_main_window)


def _task(id: str, title: str = "T", status: Status = Status.PENDING,
          deps: list[str] | None = None) -> Task:
    return Task(id=id, title=title, status=status,
                type=TaskType.AGENT, deps=deps or [])


# ── US-004: mudança de status ─────────────────────────────────────────────────


def test_status_change_pending_to_in_progress_persists(ctrl, repo):
    """US-004/AC-1: pending → in_progress persiste e recalcula setor para ACTIVE."""
    task = _task("t1", "Task 1")
    repo.create(task)

    ctrl.handle_status_change(task, "in_progress")

    updated = repo.get_by_id("t1")
    assert updated is not None
    assert updated.status == Status.IN_PROGRESS

    all_tasks = {t.id: t for t in repo.list_active()}
    has_open = count_open_deps(updated.deps, all_tasks) > 0
    sector, _ = compute_sector(updated.status, has_open)
    assert sector == Sector.ACTIVE


def test_status_change_to_done_persists_completed_at(ctrl, repo):
    """US-004/AC-1: → done preenche completed_at no banco."""
    task = _task("t1", "Task 1", status=Status.IN_PROGRESS)
    repo.create(task)

    ctrl.handle_status_change(task, "done")

    updated = repo.get_by_id("t1")
    assert updated is not None
    assert updated.status == Status.DONE
    assert updated.completed_at is not None, "completed_at deve ser preenchido ao marcar done"


def test_status_change_in_progress_to_pending_recalculates_sector(ctrl, repo):
    """US-004/AC-3: in_progress → pending recalcula setor para WAITING (sem deps)."""
    task = _task("t1", "Task 1", status=Status.IN_PROGRESS)
    repo.create(task)

    ctrl.handle_status_change(task, "pending")

    updated = repo.get_by_id("t1")
    assert updated is not None
    assert updated.status == Status.PENDING

    all_tasks = {t.id: t for t in repo.list_active()}
    has_open = count_open_deps(updated.deps, all_tasks) > 0
    sector, _ = compute_sector(updated.status, has_open)
    assert sector == Sector.WAITING


def test_status_change_blocked_task_to_in_progress_stays_in_active(ctrl, repo):
    """US-004/AC-2: task bloqueada (deps em aberto) pode ter status in_progress
    mas setor reflete ACTIVE com cor cinza (não BLOCKED)."""
    dep = _task("dep1", "Dep", status=Status.PENDING)
    task = _task("t1", "Task bloqueada", deps=["dep1"])
    repo.create(dep)
    repo.create(task)

    ctrl.handle_status_change(task, "in_progress")

    updated = repo.get_by_id("t1")
    assert updated is not None
    assert updated.status == Status.IN_PROGRESS

    all_tasks = {t.id: t for t in repo.list_active()}
    has_open = count_open_deps(updated.deps, all_tasks) > 0
    sector, color = compute_sector(updated.status, has_open)
    # in_progress com dep aberta → ACTIVE com cor GRAY (bloqueio técnico sinalizado)
    assert sector == Sector.ACTIVE
    assert color.value == "gray"


def test_status_change_calls_task_list_refresh(ctrl, repo, mock_task_list):
    """US-004: task_list.refresh é chamado após mudança de status."""
    task = _task("t1")
    repo.create(task)

    ctrl.handle_status_change(task, "in_progress")

    mock_task_list.refresh.assert_called_once()
    refreshed = mock_task_list.refresh.call_args[0][0]
    assert any(t.id == "t1" for t in refreshed)


def test_status_change_io_error_shows_error_dialog(ctrl, repo, mock_task_list):
    """US-004/AC-4: erro de I/O ao mudar status → ErrorDialog; refresh NÃO chamado."""
    task = _task("t1")
    repo.create(task)

    with patch.object(repo, "update", side_effect=sqlite3.OperationalError("disk")):
        with patch("task_manager_desktop.controllers.edit_task_controller.ErrorDialog") as mock_ed:
            ctrl.handle_status_change(task, "done")
            mock_ed.show_io_error.assert_called_once()

    mock_task_list.refresh.assert_not_called()


# ── US-005: promoção automática de dependentes ────────────────────────────────


def test_done_status_promotes_direct_dependent_to_waiting(ctrl, repo):
    """US-005/AC-1: concluir A promove B (que depende só de A) para Fila.

    A (done) → B (pending, deps=[A]) deve migrar para WAITING.
    """
    a = _task("a", "Task A", status=Status.IN_PROGRESS)
    b = _task("b", "Task B", deps=["a"])
    repo.create(a)
    repo.create(b)

    ctrl.handle_status_change(a, "done")

    tasks = {t.id: t for t in repo.list_active()}
    # A deve estar concluída (pode estar escondida ou não — depende do cleanup)
    a_or_done = repo.get_by_id("a")
    if a_or_done:
        assert a_or_done.status == Status.DONE

    # B foi buscado do banco após refresh — deve ter deps=["a"] mas a está done
    b_updated = tasks.get("b")
    assert b_updated is not None
    all_tasks = dict(tasks)
    has_open = count_open_deps(b_updated.deps, all_tasks) > 0
    sector, _ = compute_sector(b_updated.status, has_open)
    assert sector == Sector.WAITING, (
        "B deve estar em WAITING após A ser concluída (única dep aberta resolvida)"
    )


def test_done_status_keeps_dependent_blocked_if_other_deps_open(ctrl, repo):
    """US-005/AC-2: D depende de A e E (ambas abertas). Concluir A → D permanece BLOCKED."""
    a = _task("a", "Task A", status=Status.IN_PROGRESS)
    e = _task("e", "Task E", status=Status.PENDING)
    d = _task("d", "Task D", deps=["a", "e"])
    repo.create(a)
    repo.create(e)
    repo.create(d)

    ctrl.handle_status_change(a, "done")

    tasks = {t.id: t for t in repo.list_active()}
    d_updated = tasks.get("d")
    assert d_updated is not None
    has_open = count_open_deps(d_updated.deps, tasks) > 0
    sector, _ = compute_sector(d_updated.status, has_open)
    assert sector == Sector.BLOCKED, (
        "D deve permanecer BLOCKED porque E ainda está aberta"
    )


def test_reverting_done_to_pending_re_blocks_dependent(ctrl, repo):
    """US-005/AC-3: reverter A de done→pending re-bloqueia F que dependia de A."""
    # Situação: A estava done, F estava em WAITING (A era única dep)
    a = _task("a", "Task A", status=Status.DONE)
    f = _task("f", "Task F", deps=["a"])
    repo.create(a)
    repo.create(f)

    # Reverter A para pending
    ctrl.handle_status_change(a, "pending")

    tasks = {t.id: t for t in repo.list_active()}
    a_updated = tasks.get("a")
    assert a_updated is not None
    assert a_updated.status == Status.PENDING

    f_updated = tasks.get("f")
    assert f_updated is not None
    has_open = count_open_deps(f_updated.deps, tasks) > 0
    sector, _ = compute_sector(f_updated.status, has_open)
    assert sector == Sector.BLOCKED, (
        "F deve voltar para BLOCKED após A retornar a pending"
    )


def test_done_does_not_cascade_past_one_level(ctrl, repo):
    """US-005/AC-4: A → B → C (cadeia). Concluir C promove B para WAITING, A permanece BLOCKED.

    O recálculo é de UM NÍVEL apenas (sem DFS).
    """
    # Cadeia: A depende de B, B depende de C
    c = _task("c", "C", status=Status.IN_PROGRESS)
    b = _task("b", "B", deps=["c"])
    a = _task("a", "A", deps=["b"])
    repo.create(c)
    repo.create(b)
    repo.create(a)

    ctrl.handle_status_change(c, "done")

    tasks = {t.id: t for t in repo.list_active()}

    # B: dependente direto de C — deve ser promovido para WAITING
    b_updated = tasks.get("b")
    assert b_updated is not None
    b_has_open = count_open_deps(b_updated.deps, tasks) > 0
    b_sector, _ = compute_sector(b_updated.status, b_has_open)
    assert b_sector == Sector.WAITING, "B deve ir para WAITING (dep C concluída)"

    # A: dependente indireto (dep de B, não de C) — permanece BLOCKED
    a_updated = tasks.get("a")
    assert a_updated is not None
    a_has_open = count_open_deps(a_updated.deps, tasks) > 0
    a_sector, _ = compute_sector(a_updated.status, a_has_open)
    assert a_sector == Sector.BLOCKED, (
        "A deve permanecer BLOCKED — recálculo é de 1 nível apenas (B ainda está pending)"
    )
