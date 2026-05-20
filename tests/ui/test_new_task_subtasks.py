"""Criacao de subtasks direto no modal de nova task.

Cobre a secao opcional "Subtasks" do TaskFormWidget em modo criacao:
digitar -> confirmar no check -> novo input em branco; ao salvar, a task
e suas subtasks sao persistidas juntas pelo CreateTaskController.
"""

from __future__ import annotations

import sqlite3

import pytest

from task_manager_desktop.controllers.create_task_controller import CreateTaskController
from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.dialogs.edit_task_dialog import EditTaskDialog
from task_manager_desktop.ui.dialogs.new_task_dialog import NewTaskDialog
from task_manager_desktop.ui.task_list import TaskList


def test_create_dialog_has_subtask_section(qtbot):
    dlg = NewTaskDialog()
    qtbot.addWidget(dlg)
    assert dlg.form._creating is True
    assert dlg.form.subtask_input.property("testid") == "subtask-new-input"
    assert dlg.form.subtask_add_btn.property("testid") == "subtask-add-btn"


def test_edit_dialog_has_no_subtask_section(qtbot):
    task = Task(id="t1", title="X", status=Status.PENDING, type=TaskType.AGENT, deps=[])
    dlg = EditTaskDialog(task=task)
    qtbot.addWidget(dlg)
    assert dlg.form._creating is False
    assert not hasattr(dlg.form, "subtask_input")
    assert dlg.get_data()["subtasks"] == []


def test_commit_subtask_adds_row_and_clears_input(qtbot):
    dlg = NewTaskDialog()
    qtbot.addWidget(dlg)
    dlg.form.subtask_input.setText("Primeira subtask")
    dlg.form.subtask_add_btn.click()

    assert dlg.form.subtask_input.text() == ""
    assert len(dlg.form._subtask_rows) == 1
    assert dlg.form._subtask_rows[0].text() == "Primeira subtask"


def test_commit_ignores_empty_input(qtbot):
    dlg = NewTaskDialog()
    qtbot.addWidget(dlg)
    dlg.form.subtask_input.setText("   ")
    dlg.form.subtask_add_btn.click()
    assert dlg.form._subtask_rows == []


def test_get_data_includes_committed_and_pending_subtasks(qtbot):
    dlg = NewTaskDialog()
    qtbot.addWidget(dlg)
    dlg.form.title_input.setText("Task com subs")

    dlg.form.subtask_input.setText("Sub A")
    dlg.form.subtask_add_btn.click()
    dlg.form.subtask_input.setText("Sub B")
    dlg.form.subtask_add_btn.click()
    # Texto ainda nao confirmado tambem entra ao salvar.
    dlg.form.subtask_input.setText("Sub C nao confirmada")

    data = dlg.get_data()
    assert data["subtasks"] == ["Sub A", "Sub B", "Sub C nao confirmada"]


def test_remove_committed_subtask_row(qtbot):
    dlg = NewTaskDialog()
    qtbot.addWidget(dlg)
    dlg.form.subtask_input.setText("Sub A")
    dlg.form.subtask_add_btn.click()
    dlg.form.subtask_input.setText("Sub B")
    dlg.form.subtask_add_btn.click()

    first_edit = dlg.form._subtask_rows[0]
    dlg.form._remove_subtask_row(first_edit.parentWidget(), first_edit)

    assert dlg.get_data()["subtasks"] == ["Sub B"]


def test_controller_persists_task_with_subtasks(qtbot, tmp_path):
    db_path = tmp_path / "subs.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    repo = TaskRepository(conn, db_path=str(db_path))
    task_list = TaskList()
    qtbot.addWidget(task_list)
    ctrl = CreateTaskController(repo, task_list, task_list, parent=None)

    data = {
        "title": "Task com subtasks",
        "type": TaskType.AGENT,
        "deps": [],
        "subtasks": ["Primeira", "Segunda", "Terceira"],
    }
    assert ctrl._persist(data, None) is True

    tasks = repo.list_active()
    assert len(tasks) == 1
    subtasks = repo.list_subtasks(tasks[0].id)
    assert [s.text for s in subtasks] == ["Primeira", "Segunda", "Terceira"]
    assert [s.order_index for s in subtasks] == [1, 2, 3]


@pytest.mark.parametrize("missing_key", [True, False])
def test_controller_handles_absent_subtasks_key(qtbot, tmp_path, missing_key):
    db_path = tmp_path / "nosubs.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    repo = TaskRepository(conn, db_path=str(db_path))
    task_list = TaskList()
    qtbot.addWidget(task_list)
    ctrl = CreateTaskController(repo, task_list, task_list, parent=None)

    data = {"title": "Sem subs", "type": TaskType.DEV, "deps": []}
    if not missing_key:
        data["subtasks"] = []
    assert ctrl._persist(data, None) is True

    tasks = repo.list_active()
    assert len(tasks) == 1
    assert repo.list_subtasks(tasks[0].id) == []
