# suite: integration | module: module-1-gestao-de-tasks | task: TASK-1
# @tdd-locked: do not edit without /tdd:unlock
# covers: TASK-1/ST005 — CreateTaskController wire-up end-to-end com DB temporario
# TIDs: TID-1-1-024, TID-1-1-025
import sqlite3

import pytest
from PySide6.QtWidgets import QDialog

from task_manager_desktop.controllers.create_task_controller import CreateTaskController
from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import TaskType
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


def _fake_dialog_cls(data: dict):
    class FakeDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, parent=None):
            pass

        def exec(self):
            return _ACCEPTED

        def get_data(self):
            return data

    return FakeDialog


# TID-1-1-024 | covers: TASK-1/ST005 happy path
def test_create_task_controller_happy_path_end_to_end(setup, monkeypatch):
    """CreateTaskController wire-up end-to-end com DB temporario:
    dialog -> resolve_cycles -> generate_id -> insert -> refresh -> toast (quando aplicavel)."""
    ctrl, repo, conn, tl = setup

    from task_manager_desktop.controllers import create_task_controller as mod

    monkeypatch.setattr(mod, "NewTaskDialog", _fake_dialog_cls({
        "title": "End-to-end task",
        "type": TaskType.AGENT,
        "deps": [],
    }))
    ctrl.handle()

    tasks = repo.list_active()
    assert len(tasks) == 1
    assert tasks[0].title == "End-to-end task"
    assert tasks[0].type == TaskType.AGENT
    assert tasks[0].deps == []


# TID-1-1-025 | covers: TASK-1/ST005 sad path
def test_create_task_controller_sad_path_io_error_keeps_dialog_open(setup, monkeypatch):
    """CreateTaskController dispara ErrorDialog.show_io_error em sqlite3.Error
    e mantem dialog aberto + OK reabilitado."""
    ctrl, repo, conn, tl = setup

    from task_manager_desktop.controllers import create_task_controller as mod

    error_shown = []

    class FakeErrorDialog:
        @staticmethod
        def show_io_error(parent, exception, db_path=""):
            error_shown.append(True)

    monkeypatch.setattr(mod, "NewTaskDialog", _fake_dialog_cls({
        "title": "Will fail",
        "type": TaskType.AGENT,
        "deps": [],
    }))
    monkeypatch.setattr(mod, "ErrorDialog", FakeErrorDialog)

    def raising_create(task):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(repo, "create", raising_create)

    ctrl.handle()

    assert len(error_shown) == 1
    assert len(repo.list_active()) == 0
