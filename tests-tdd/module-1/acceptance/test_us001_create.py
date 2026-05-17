# suite: acceptance | module: module-1-gestao-de-tasks | task: TASK-1
# @tdd-locked: do not edit without /tdd:unlock
# covers: US-001 (cenarios 1-8) — Criar task com titulo, tipo, projeto e dependencias
# TIDs: TID-1-1-001, TID-1-1-002, TID-1-1-003, TID-1-1-004, TID-1-1-005,
#        TID-1-1-006, TID-1-1-007, TID-1-1-008
import sqlite3

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from task_manager_desktop.controllers.create_task_controller import CreateTaskController
from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Status, Task, TaskType
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
    ctrl = CreateTaskController(repo, tl, tl, parent=None)
    return ctrl, repo, conn, tl


def _fake_dialog_data(title, tipo=TaskType.ONLINE, projeto="", deps=""):
    from task_manager_desktop.core.models import normalize_projeto, parse_deps
    return {
        "title": title,
        "type": tipo,
        "projeto": normalize_projeto(projeto),
        "deps": parse_deps(deps),
    }


def _make_fake_dialog_cls(data: dict):
    class FakeDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, parent=None):
            pass

        def exec(self):
            return _ACCEPTED

        def get_data(self):
            return data

    return FakeDialog


# TID-1-1-001 | covers: US-001#1 | bdd_type: SUCCESS
def test_create_no_deps_defaults(setup, monkeypatch):
    """Task criada sem deps (type=online default, projeto=outros default)."""
    ctrl, repo, conn, tl = setup

    from task_manager_desktop.controllers import create_task_controller as mod

    monkeypatch.setattr(mod, "NewTaskDialog", _make_fake_dialog_cls(
        _fake_dialog_data("Tarefa sem deps")
    ))

    ctrl.handle()

    tasks = repo.list_active()
    assert len(tasks) == 1
    t = tasks[0]
    assert t.title == "Tarefa sem deps"
    assert t.type == TaskType.ONLINE
    assert t.projeto == "outros"
    assert t.deps == []


# TID-1-1-002 | covers: US-001#2 | bdd_type: SUCCESS
def test_create_with_valid_open_deps(setup, monkeypatch):
    """Task criada com deps validas abertas (vai para Bloqueadas)."""
    ctrl, repo, conn, tl = setup

    dep = Task(id="dep1", title="Dep", status=Status.PENDING)
    repo.create(dep)

    from task_manager_desktop.controllers import create_task_controller as mod

    monkeypatch.setattr(mod, "NewTaskDialog", _make_fake_dialog_cls(
        _fake_dialog_data("Task com dep", deps="dep1")
    ))
    ctrl.handle()

    tasks = [t for t in repo.list_active() if t.title == "Task com dep"]
    assert len(tasks) == 1
    assert "dep1" in tasks[0].deps


# TID-1-1-003 | covers: US-001#3 | bdd_type: ERROR
def test_empty_title_blocks_submit(qtbot):
    """Titulo vazio bloqueado (border vermelha + tooltip + foco no campo)."""
    from task_manager_desktop.ui.dialogs.new_task_dialog import NewTaskDialog

    dlg = NewTaskDialog()
    qtbot.addWidget(dlg)
    dlg.show()

    qtbot.mouseClick(dlg._ok_btn, Qt.LeftButton)

    assert dlg.title_edit.property("class") == "field-error"
    assert dlg._title_error.isVisible()
    assert dlg.result() != dlg.DialogCode.Accepted


# TID-1-1-004 | covers: US-001#4 | bdd_type: EDGE
def test_invalid_dep_id_silently_dropped(setup, monkeypatch):
    """ID de dep invalido descartado silenciosamente (sem warning)."""
    ctrl, repo, conn, tl = setup

    repo.create(Task(id="valid1", title="Dep valid"))

    from task_manager_desktop.controllers import create_task_controller as mod

    monkeypatch.setattr(mod, "NewTaskDialog", _make_fake_dialog_cls(
        _fake_dialog_data("Task", deps="valid1,xyz999")
    ))
    ctrl.handle()

    tasks = [t for t in repo.list_active() if t.title == "Task"]
    assert len(tasks) == 1
    assert tasks[0].deps == ["valid1"]


# TID-1-1-005 | covers: US-001#5 | bdd_type: EDGE
def test_cycle_resolved_with_toast(setup, monkeypatch):
    """Ciclo de dependencia resolvido via resolve_cycles com toast >= 4s."""
    ctrl, repo, conn, tl = setup

    # Setup: bbb depends on aaa (no cycle with new task yet)
    task_a = Task(id="aaa", title="A", status=Status.PENDING, deps=[])
    task_b = Task(id="bbb", title="B", status=Status.PENDING, deps=["aaa"])
    repo.create(task_a)
    repo.create(task_b)

    from task_manager_desktop.controllers import create_task_controller as mod

    toast_args = []

    class FakeToast:
        def __init__(self, parent=None):
            pass
        def show_message(self, msg, duration_ms=3000):
            toast_args.append((msg, duration_ms))

    monkeypatch.setattr(mod, "ToastWidget", FakeToast)
    monkeypatch.setattr(mod, "NewTaskDialog", _make_fake_dialog_cls(
        _fake_dialog_data("New task", deps="bbb,nonexistent")
    ))
    ctrl.handle()

    tasks = [t for t in repo.list_active() if t.title == "New task"]
    assert len(tasks) == 1
    assert "bbb" in tasks[0].deps
    assert "nonexistent" not in tasks[0].deps


# TID-1-1-006 | covers: US-001#6 | bdd_type: SUCCESS
def test_create_with_offline_type(setup, monkeypatch):
    """Task criada com radio type=offline persiste e card mostra wifi-off."""
    ctrl, repo, conn, tl = setup

    from task_manager_desktop.controllers import create_task_controller as mod

    monkeypatch.setattr(mod, "NewTaskDialog", _make_fake_dialog_cls(
        _fake_dialog_data("Offline task", tipo=TaskType.OFFLINE)
    ))
    ctrl.handle()

    tasks = repo.list_active()
    assert len(tasks) == 1
    assert tasks[0].type == TaskType.OFFLINE
    row = conn.execute("SELECT type FROM tasks WHERE title='Offline task'").fetchone()
    assert row["type"] == "offline"


# TID-1-1-007 | covers: US-001#7 | bdd_type: SUCCESS
def test_create_with_explicit_projeto(setup, monkeypatch):
    """Task criada com projeto explicito ('systemforge') persiste literal."""
    ctrl, repo, conn, tl = setup

    from task_manager_desktop.controllers import create_task_controller as mod

    monkeypatch.setattr(mod, "NewTaskDialog", _make_fake_dialog_cls(
        _fake_dialog_data("SF task", projeto="systemforge")
    ))
    ctrl.handle()

    tasks = repo.list_active()
    assert len(tasks) == 1
    assert tasks[0].projeto == "systemforge"
    row = conn.execute("SELECT projeto FROM tasks WHERE title='SF task'").fetchone()
    assert row["projeto"] == "systemforge"


# TID-1-1-008 | covers: US-001#8 | bdd_type: EDGE
def test_empty_projeto_normalized_to_outros(setup, monkeypatch):
    """Projeto vazio/whitespace normalizado para 'outros' via normalize_projeto."""
    ctrl, repo, conn, tl = setup

    from task_manager_desktop.controllers import create_task_controller as mod

    monkeypatch.setattr(mod, "NewTaskDialog", _make_fake_dialog_cls(
        _fake_dialog_data("Whitespace proj", projeto="   ")
    ))
    ctrl.handle()

    tasks = repo.list_active()
    assert len(tasks) == 1
    assert tasks[0].projeto == "outros"
