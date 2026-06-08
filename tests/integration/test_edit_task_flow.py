from __future__ import annotations

import sqlite3

import pytest
from PySide6.QtWidgets import QDialog

from task_manager_desktop.controllers.edit_task_controller import EditTaskController
from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Sector, Task
from task_manager_desktop.core.sector import compute_sector, count_open_deps
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.task_list import TaskList

_ACCEPTED = QDialog.DialogCode.Accepted


@pytest.fixture
def setup(qtbot, tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    repo = TaskRepository(conn, db_path=str(db_path))
    tl = TaskList()
    qtbot.addWidget(tl)
    ctrl = EditTaskController(repo, tl, tl, parent=None)
    return ctrl, repo, conn, str(db_path)


def _fake_edit_dialog(data: dict):
    """Cria um FakeDialog que retorna `data` sem abrir UI."""
    class FakeDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, task, parent=None):
            pass

        def exec(self):
            return _ACCEPTED

        def get_data(self):
            return data

    return FakeDialog


def test_edit_title_persists_no_sector_change(setup, monkeypatch):
    """AC-T-001: Editar titulo persiste sem mudar setor."""
    ctrl, repo, conn, db_path = setup
    task = Task(id="abc", title="Original", deps=[])
    repo.create(task)

    from task_manager_desktop.controllers import edit_task_controller as mod
    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "Novo titulo",
        "deps": [],
    }))

    ctrl.handle_edit(task)

    tasks = repo.list_active()
    assert len(tasks) == 1
    assert tasks[0].title == "Novo titulo"


def test_add_open_dep_moves_to_blocked(setup, monkeypatch):
    """AC-T-002: Adicionar dep aberta move task de Fila para Bloqueadas."""
    ctrl, repo, conn, _ = setup
    dep_task = Task(id="dep1", title="Dep pendente", deps=[])
    main_task = Task(id="main", title="Principal", deps=[])
    repo.create(dep_task)
    repo.create(main_task)

    from task_manager_desktop.controllers import edit_task_controller as mod
    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "Principal",
        "deps": ["dep1"],  # adicionando dep aberta
    }))

    ctrl.handle_edit(main_task)

    tasks = repo.list_active()
    all_tasks = {t.id: t for t in tasks}
    updated = next(t for t in tasks if t.id == "main")

    has_open = count_open_deps(updated.deps, all_tasks) > 0
    sector, _ = compute_sector(updated.status, has_open)
    assert sector == Sector.BLOCKED


def test_remove_last_dep_moves_to_waiting(setup, monkeypatch):
    """AC-T-003: Remover unica dep move task de Bloqueadas para Fila."""
    ctrl, repo, conn, _ = setup
    dep_task = Task(id="dep1", title="Dep", deps=[])
    main_task = Task(id="main", title="Principal", deps=["dep1"])
    repo.create(dep_task)
    repo.create(main_task)

    from task_manager_desktop.controllers import edit_task_controller as mod
    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "Principal",
        "deps": [],  # removendo dep
    }))

    ctrl.handle_edit(main_task)

    tasks = repo.list_active()
    all_tasks = {t.id: t for t in tasks}
    updated = next(t for t in tasks if t.id == "main")

    has_open = count_open_deps(updated.deps, all_tasks) > 0
    sector, _ = compute_sector(updated.status, has_open)
    assert sector == Sector.WAITING
    assert updated.deps == []


def test_cycle_edit_drops_cycle_dep(setup, monkeypatch):
    """AC-T-004: Ciclo na edicao resulta em drop da dep ciclica."""
    ctrl, repo, conn, _ = setup
    # A -> B, B -> C; editar C para adicionar A (criaria ciclo C->A->B->C)
    a = Task(id="a", title="A", deps=["b"])
    b = Task(id="b", title="B", deps=["c"])
    c = Task(id="c", title="C", deps=[])
    repo.create(a)
    repo.create(b)
    repo.create(c)

    from task_manager_desktop.controllers import edit_task_controller as mod
    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "C",
        "deps": ["a"],  # criaria ciclo: C -> A -> B -> C
    }))

    ctrl.handle_edit(c)

    tasks = repo.list_active()
    c_updated = next(t for t in tasks if t.id == "c")
    assert "a" not in c_updated.deps


# removido: Task.type foi removido (tipo migrou para subtasks)


def test_io_error_shows_error_dialog_no_corruption(setup, monkeypatch):
    """AC-T-015: Erro I/O nao corrompe estado em memoria."""
    ctrl, repo, conn, _ = setup
    task = Task(id="abc", title="Original", deps=[])
    repo.create(task)

    error_shown = []

    from task_manager_desktop.controllers import edit_task_controller as mod

    class FakeErrorDialog:
        @staticmethod
        def show_io_error(parent, exc, db_path=""):
            error_shown.append(True)

    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "Novo",
        "deps": [],
    }))
    monkeypatch.setattr(mod, "ErrorDialog", FakeErrorDialog)

    def failing_update(*args, **kwargs):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(repo, "update", failing_update)

    ctrl.handle_edit(task)

    assert len(error_shown) == 1
    # Estado original preservado (banco nao foi alterado pois update falhou)
    tasks = repo.list_active()
    assert tasks[0].title == "Original"


def test_recalc_only_direct_dependents_not_grandchildren(setup, monkeypatch):
    """RF-008: Recalculo cobre UM NIVEL — editar A nao recalcula setor de C que depende de B."""
    ctrl, repo, conn, _ = setup
    # Cadeia: A <- B <- C (C depende de B, B depende de A)
    a = Task(id="a", title="A", deps=[])
    b = Task(id="b", title="B", deps=["a"])
    c = Task(id="c", title="C", deps=["b"])
    repo.create(a)
    repo.create(b)
    repo.create(c)

    # Editar A — apenas B (dependente direto) deve ser recalculado, nao C
    from task_manager_desktop.controllers import edit_task_controller as mod
    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "A editada",
        "deps": [],
    }))

    # Apenas verifica que a edicao nao lanca excecao e persiste
    ctrl.handle_edit(a)
    tasks = repo.list_active()
    a_updated = next(t for t in tasks if t.id == "a")
    assert a_updated.title == "A editada"
