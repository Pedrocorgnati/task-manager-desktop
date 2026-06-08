# suite: acceptance | module: module-1-gestao-de-tasks | tasks: TASK-1/ST005, TASK-2/ST003
# @tdd-locked: do not edit without /tdd:unlock
# covers: US-016 — Feedback de erro claro e acionavel em falhas de I/O (criar + editar)
# TIDs: TID-1-1-011, TID-1-2-009
from __future__ import annotations

import sqlite3

import pytest
from PySide6.QtWidgets import QDialog

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Task
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


class _FakeErrorDialog:
    _calls = []

    @staticmethod
    def show_io_error(parent, exc, db_path=""):
        _FakeErrorDialog._calls.append(True)


# TID-1-1-011 | covers: US-016#1 | bdd_type: ERROR
def test_create_io_error_shows_dialog(_setup, monkeypatch, qtbot):
    """I/O error em CreateTaskController dispara ErrorDialog.show_io_error e mantem dialog aberto."""
    repo, conn, tl, db_path = _setup

    from task_manager_desktop.controllers import create_task_controller as mod
    from task_manager_desktop.controllers.create_task_controller import CreateTaskController

    ctrl = CreateTaskController(repo, tl, tl, parent=None)

    error_shown = []

    class FakeErrorDialog:
        @staticmethod
        def show_io_error(parent, exc, db_path=""):
            error_shown.append(True)

    monkeypatch.setattr(mod, "NewTaskDialog", _fake_create_dialog({
        "title": "Nova task",
        "deps": [],
    }))
    monkeypatch.setattr(mod, "ErrorDialog", FakeErrorDialog)

    def failing_create(*args, **kwargs):
        raise sqlite3.OperationalError("disk I/O error")
    monkeypatch.setattr(repo, "create", failing_create)

    ctrl.handle()

    assert len(error_shown) == 1
    assert len(repo.list_active()) == 0


# TID-1-2-009 | covers: US-016#2 | bdd_type: ERROR
def test_edit_io_error_shows_dialog(_setup, monkeypatch, qtbot):
    """I/O error em EditTaskController dispara ErrorDialog e Salvar reabilita."""
    repo, conn, tl, db_path = _setup

    task = Task(id="t1", title="Original", deps=[])
    repo.create(task)

    from task_manager_desktop.controllers import edit_task_controller as mod
    from task_manager_desktop.controllers.edit_task_controller import EditTaskController

    ctrl = EditTaskController(repo, tl, tl, parent=None)

    error_shown = []

    class FakeErrorDialog:
        @staticmethod
        def show_io_error(parent, exc, db_path=""):
            error_shown.append(True)

    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "Novo titulo",
        "deps": [],
    }))
    monkeypatch.setattr(mod, "ErrorDialog", FakeErrorDialog)

    def failing_update(*args, **kwargs):
        raise sqlite3.OperationalError("disk I/O error")
    monkeypatch.setattr(repo, "update", failing_update)

    ctrl.handle_edit(task)

    assert len(error_shown) == 1
    tasks = repo.list_active()
    assert tasks[0].title == "Original"
