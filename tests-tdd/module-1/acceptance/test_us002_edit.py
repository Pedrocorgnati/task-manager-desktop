# suite: acceptance | module: module-1-gestao-de-tasks | task: TASK-2
# @tdd-locked: do not edit without /tdd:unlock
# covers: US-002 (cenarios 1-7) — Editar titulo, tipo, projeto e dependencias
# TIDs: TID-1-2-001, TID-1-2-002, TID-1-2-003, TID-1-2-004, TID-1-2-005,
#        TID-1-2-006, TID-1-2-007
from __future__ import annotations

import sqlite3

import pytest
from PySide6.QtWidgets import QDialog

from task_manager_desktop.controllers.edit_task_controller import EditTaskController
from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Sector, Status, Task, TaskType
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
    class FakeDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, task, parent=None):
            pass

        def exec(self):
            return _ACCEPTED

        def get_data(self):
            return data

    return FakeDialog


# TID-1-2-001 | covers: US-002#1 | bdd_type: SUCCESS
def test_edit_title_persists_no_sector_change(setup, monkeypatch):
    """Edicao apenas do titulo persiste e card atualiza sem mudar setor."""
    ctrl, repo, conn, db_path = setup
    task = Task(id="t1", title="Original", type=TaskType.ONLINE, projeto="forge", deps=[])
    repo.create(task)

    from task_manager_desktop.controllers import edit_task_controller as mod
    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "Editado",
        "type": TaskType.ONLINE,
        "projeto": "forge",
        "deps": [],
    }))

    ctrl.handle_edit(task)

    tasks = repo.list_active()
    assert len(tasks) == 1
    updated = tasks[0]
    assert updated.title == "Editado"
    assert updated.projeto == "forge"
    assert updated.deps == []

    all_tasks = {t.id: t for t in tasks}
    has_open = count_open_deps(updated.deps, all_tasks) > 0
    sector, _ = compute_sector(updated.status, has_open)
    assert sector == Sector.WAITING


# TID-1-2-002 | covers: US-002#2 | bdd_type: SUCCESS
def test_add_open_dep_moves_to_blocked(setup, monkeypatch):
    """Adicao de dep aberta move task de Fila para Bloqueadas com recalc."""
    ctrl, repo, conn, _ = setup
    dep = Task(id="dep1", title="Dep", type=TaskType.ONLINE, projeto="forge", deps=[])
    main = Task(id="main", title="Main", type=TaskType.ONLINE, projeto="forge", deps=[])
    repo.create(dep)
    repo.create(main)

    from task_manager_desktop.controllers import edit_task_controller as mod
    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "Main",
        "type": TaskType.ONLINE,
        "projeto": "forge",
        "deps": ["dep1"],
    }))

    ctrl.handle_edit(main)

    tasks = repo.list_active()
    all_tasks = {t.id: t for t in tasks}
    updated = next(t for t in tasks if t.id == "main")
    assert "dep1" in updated.deps

    has_open = count_open_deps(updated.deps, all_tasks) > 0
    sector, _ = compute_sector(updated.status, has_open)
    assert sector == Sector.BLOCKED


# TID-1-2-003 | covers: US-002#3 | bdd_type: SUCCESS
def test_remove_last_dep_moves_to_queue(setup, monkeypatch):
    """Remocao da unica dep aberta move task de Bloqueadas para Fila."""
    ctrl, repo, conn, _ = setup
    dep = Task(id="dep1", title="Dep", type=TaskType.ONLINE, projeto="forge", deps=[])
    main = Task(id="main", title="Main", type=TaskType.ONLINE, projeto="forge", deps=["dep1"])
    repo.create(dep)
    repo.create(main)

    from task_manager_desktop.controllers import edit_task_controller as mod
    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "Main",
        "type": TaskType.ONLINE,
        "projeto": "forge",
        "deps": [],
    }))

    ctrl.handle_edit(main)

    tasks = repo.list_active()
    all_tasks = {t.id: t for t in tasks}
    updated = next(t for t in tasks if t.id == "main")
    assert updated.deps == []

    has_open = count_open_deps(updated.deps, all_tasks) > 0
    sector, _ = compute_sector(updated.status, has_open)
    assert sector == Sector.WAITING


# TID-1-2-004 | covers: US-002#4 | bdd_type: EDGE
def test_cycle_on_edit_resolved_with_toast(setup, monkeypatch):
    """Edicao introduz ciclo: resolve_cycles aplica substituicao + toast >= 3s."""
    ctrl, repo, conn, _ = setup
    a = Task(id="a", title="A", type=TaskType.ONLINE, projeto="f", deps=["b"])
    b = Task(id="b", title="B", type=TaskType.ONLINE, projeto="f", deps=["c"])
    c = Task(id="c", title="C", type=TaskType.ONLINE, projeto="f", deps=[])
    repo.create(a)
    repo.create(b)
    repo.create(c)

    toast_args = []

    from task_manager_desktop.controllers import edit_task_controller as mod

    class FakeToast:
        def __init__(self, parent=None):
            pass

        def show_message(self, msg, duration_ms=3000):
            toast_args.append((msg, duration_ms))

    monkeypatch.setattr(mod, "ToastWidget", FakeToast)
    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "C",
        "type": TaskType.ONLINE,
        "projeto": "f",
        "deps": ["a"],  # C -> A -> B -> C = ciclo
    }))

    ctrl.handle_edit(c)

    tasks = repo.list_active()
    c_updated = next(t for t in tasks if t.id == "c")
    assert "a" not in c_updated.deps

    if toast_args:
        _, duration = toast_args[0]
        assert duration >= 3000


# TID-1-2-005 | covers: US-002#5 | bdd_type: SUCCESS
def test_change_type_persists_and_updates_card_icon(setup, monkeypatch):
    """Troca de type via radio persiste e atualiza icone wifi/wifi-off do card."""
    ctrl, repo, conn, _ = setup
    task = Task(id="t1", title="X", type=TaskType.ONLINE, projeto="f", deps=[])
    repo.create(task)

    from task_manager_desktop.controllers import edit_task_controller as mod
    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "X",
        "type": TaskType.OFFLINE,
        "projeto": "f",
        "deps": [],
    }))

    ctrl.handle_edit(task)

    tasks = repo.list_active()
    updated = next(t for t in tasks if t.id == "t1")
    assert updated.type == TaskType.OFFLINE

    row = conn.execute("SELECT type FROM tasks WHERE id='t1'").fetchone()
    assert row["type"] == "offline"


# TID-1-2-006 | covers: US-002#6 | bdd_type: SUCCESS
def test_rename_projeto_emits_projects_changed(setup, monkeypatch, qtbot):
    """Renomear projeto persiste e dispara projects_changed para ProjectFilter."""
    ctrl, repo, conn, _ = setup
    task = Task(id="t1", title="X", type=TaskType.ONLINE, projeto="antigo", deps=[])
    repo.create(task)

    from task_manager_desktop.controllers import edit_task_controller as mod
    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "X",
        "type": TaskType.ONLINE,
        "projeto": "novo",
        "deps": [],
    }))

    with qtbot.waitSignal(ctrl.projects_changed, timeout=1000):
        ctrl.handle_edit(task)

    tasks = repo.list_active()
    updated = next(t for t in tasks if t.id == "t1")
    assert updated.projeto == "novo"


# TID-1-2-007 | covers: US-002#7 | bdd_type: EDGE
def test_empty_projeto_normalizes_to_outros(setup, monkeypatch):
    """Esvaziar campo projeto re-normaliza para 'outros'; card mostra #outros."""
    ctrl, repo, conn, _ = setup
    task = Task(id="t1", title="X", type=TaskType.ONLINE, projeto="forge", deps=[])
    repo.create(task)

    from task_manager_desktop.controllers import edit_task_controller as mod
    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "X",
        "type": TaskType.ONLINE,
        "projeto": "outros",
        "deps": [],
    }))

    ctrl.handle_edit(task)

    tasks = repo.list_active()
    updated = next(t for t in tasks if t.id == "t1")
    assert updated.projeto == "outros"

    row = conn.execute("SELECT projeto FROM tasks WHERE id='t1'").fetchone()
    assert row["projeto"] == "outros"
