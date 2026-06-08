from __future__ import annotations

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
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    repo = TaskRepository(conn, db_path=str(tmp_path / "test.db"))
    tl = TaskList()
    qtbot.addWidget(tl)
    ctrl = CreateTaskController(repo, tl, tl, parent=None)
    return ctrl, repo


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


def test_created_subtasks_use_default_type(setup, monkeypatch):
    """O tipo migrou para as subtasks e o card/task nao tem mais tipo proprio:
    as subtasks criadas no dialog de nova task nascem com o tipo default (agent),
    sendo ajustadas depois na subtask pane."""
    ctrl, repo = setup
    from task_manager_desktop.controllers import create_task_controller as mod

    monkeypatch.setattr(
        mod,
        "NewTaskDialog",
        _fake_dialog_cls(
            {
                "title": "Task com subtasks",
                "deps": [],
                "subtasks": ["primeira", "segunda"],
            }
        ),
    )
    ctrl.handle()

    [task] = repo.list_active()
    subs = repo.list_subtasks(task.id)
    assert {s.text for s in subs} == {"primeira", "segunda"}
    assert all(s.type is TaskType.AGENT for s in subs)
