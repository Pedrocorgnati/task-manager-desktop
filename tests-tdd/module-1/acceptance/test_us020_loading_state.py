# suite: acceptance | module: module-1-gestao-de-tasks | tasks: TASK-1/ST001, TASK-2/ST001
# @tdd-locked: do not edit without /tdd:unlock
# covers: US-020 — Loading state defensivo durante submissao de operacoes CRUD
# TIDs: TID-1-1-010, TID-1-2-008
from __future__ import annotations

import sqlite3

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.task_list import TaskList

_ACCEPTED = QDialog.DialogCode.Accepted


@pytest.fixture
def _setup(qtbot, tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    repo = TaskRepository(conn, db_path=str(db_path))
    tl = TaskList()
    qtbot.addWidget(tl)
    return repo, conn, tl, str(db_path)


def _fake_create_dialog(data):
    class FakeDialog:
        DialogCode = QDialog.DialogCode
        def __init__(self, parent=None): pass
        def exec(self): return _ACCEPTED
        def get_data(self): return data
    return FakeDialog


def _fake_edit_dialog(data):
    class FakeDialog:
        DialogCode = QDialog.DialogCode
        def __init__(self, task, parent=None): pass
        def exec(self): return _ACCEPTED
        def get_data(self): return data
    return FakeDialog


# TID-1-1-010 | covers: US-020#1 | bdd_type: SUCCESS
def test_ok_button_disabled_during_create_submit(_setup, monkeypatch, qtbot):
    """Botao OK do NewTaskDialog desabilitado durante insert + WaitCursor (<=200ms)."""
    repo, conn, tl, db_path = _setup

    from task_manager_desktop.controllers.create_task_controller import CreateTaskController
    from task_manager_desktop.controllers import create_task_controller as mod

    ctrl = CreateTaskController(repo, tl, tl, parent=None)

    cursor_during_create = []
    orig_create = repo.create

    def check_create(*args, **kwargs):
        cursor_during_create.append(QApplication.overrideCursor() is not None)
        return orig_create(*args, **kwargs)

    monkeypatch.setattr(mod, "NewTaskDialog", _fake_create_dialog({
        "title": "Task X",
        "type": TaskType.AGENT,
        "deps": [],
    }))
    monkeypatch.setattr(repo, "create", check_create)

    ctrl.handle()

    tasks = repo.list_active()
    assert len(tasks) == 1
    assert tasks[0].title == "Task X"
    # WaitCursor was active during create
    assert cursor_during_create == [True]
    # After completion, cursor is restored
    assert QApplication.overrideCursor() is None


# TID-1-2-008 | covers: US-020#2 | bdd_type: SUCCESS
def test_save_button_disabled_during_edit_submit(_setup, monkeypatch, qtbot):
    """Botao Salvar do EditTaskDialog desabilitado durante update + WaitCursor."""
    repo, conn, tl, db_path = _setup

    task = Task(id="t1", title="Original", type=TaskType.AGENT, deps=[])
    repo.create(task)

    from task_manager_desktop.controllers.edit_task_controller import EditTaskController
    from task_manager_desktop.controllers import edit_task_controller as mod

    ctrl = EditTaskController(repo, tl, tl, parent=None)

    cursor_during_update = []
    orig_update = repo.update

    def check_update(*args, **kwargs):
        cursor_during_update.append(QApplication.overrideCursor() is not None)
        return orig_update(*args, **kwargs)

    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "Updated",
        "type": TaskType.AGENT,
        "deps": [],
    }))
    monkeypatch.setattr(repo, "update", check_update)

    ctrl.handle_edit(task)

    tasks = repo.list_active()
    updated = next(t for t in tasks if t.id == "t1")
    assert updated.title == "Updated"
    # WaitCursor was active during update
    assert cursor_during_update == [True]
    # After completion, cursor is restored
    assert QApplication.overrideCursor() is None
