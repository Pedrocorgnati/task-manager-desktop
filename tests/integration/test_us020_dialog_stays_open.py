# suite: integration | module: module-1-gestao-de-tasks | task: TASK-4/ST003
# covers: US-020 c3 — dialog permanece aberto em erro de I/O para nova tentativa
# TIDs: TID-1-4-001 (create), TID-1-4-002 (edit)
from __future__ import annotations

import sqlite3

import pytest
from PySide6.QtWidgets import QDialog, QDialogButtonBox

from task_manager_desktop.controllers.create_task_controller import CreateTaskController
from task_manager_desktop.controllers.edit_task_controller import EditTaskController
from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.dialogs.edit_task_dialog import EditTaskDialog
from task_manager_desktop.ui.dialogs.new_task_dialog import NewTaskDialog
from task_manager_desktop.ui.task_list import TaskList


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


# TID-1-4-001 | covers: US-020#3 SAD path create
def test_create_dialog_stays_open_on_io_error(_setup, monkeypatch, qtbot):
    """US-020 c3: NewTaskDialog permanece aberto + OK reabilitado quando repo.create levanta sqlite3.Error."""
    repo, conn, tl, db_path = _setup

    from task_manager_desktop.controllers import create_task_controller as mod

    error_shown = []

    class FakeErrorDialog:
        @staticmethod
        def show_io_error(parent, exception, db_path=""):
            error_shown.append(True)

    monkeypatch.setattr(mod, "ErrorDialog", FakeErrorDialog)

    def raising_create(task):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(repo, "create", raising_create)

    ctrl = CreateTaskController(repo, tl, tl, parent=None)
    dialog = NewTaskDialog(parent=tl)
    qtbot.addWidget(dialog)
    dialog.submit_handler = lambda data: ctrl._persist(data, tl)
    dialog.form.title_input.setText("Will fail")

    dialog._on_accept()

    ok_btn = dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)
    assert ok_btn.isEnabled() is True, "OK deve voltar habilitado apos erro de I/O"
    assert dialog.result() != QDialog.DialogCode.Accepted, "Dialog NAO deve ter sido aceito"
    assert len(error_shown) == 1, "ErrorDialog.show_io_error deve ter sido chamado"
    assert len(repo.list_active()) == 0, "Nenhuma task deve ter sido persistida"


# TID-1-4-002 | covers: US-020#3 SAD path edit
def test_edit_dialog_stays_open_on_io_error(_setup, monkeypatch, qtbot):
    """US-020 c3: EditTaskDialog permanece aberto + Salvar reabilitado quando repo.update levanta sqlite3.Error."""
    repo, conn, tl, db_path = _setup

    task = Task(id="t1", title="Original", type=TaskType.AGENT, deps=[])
    repo.create(task)

    from task_manager_desktop.controllers import edit_task_controller as mod

    error_shown = []

    class FakeErrorDialog:
        @staticmethod
        def show_io_error(parent, exception, db_path=""):
            error_shown.append(True)

    monkeypatch.setattr(mod, "ErrorDialog", FakeErrorDialog)

    def raising_update(*args, **kwargs):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(repo, "update", raising_update)

    ctrl = EditTaskController(repo, tl, tl, parent=None)
    dialog = EditTaskDialog(task, parent=tl)
    qtbot.addWidget(dialog)
    dialog.submit_handler = lambda data: ctrl._persist(task, data, tl)
    dialog.form.title_input.setText("Updated")

    dialog._on_accept()

    ok_btn = dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)
    assert ok_btn.isEnabled() is True, "Salvar deve voltar habilitado apos erro de I/O"
    assert dialog.result() != QDialog.DialogCode.Accepted, "Dialog NAO deve ter sido aceito"
    assert len(error_shown) == 1, "ErrorDialog.show_io_error deve ter sido chamado"
    persisted = repo.list_active()[0]
    assert persisted.title == "Original", "Update NAO deve ter sido persistido"
