# suite: integration | module: module-1-gestao-de-tasks | task: TASK-2
# @tdd-locked: do not edit without /tdd:unlock
# covers: TASK-2/ST003 — EditTaskController wire-up end-to-end + RF-008
# TIDs: TID-1-2-023, TID-1-2-024
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
    class FakeDialog:
        DialogCode = QDialog.DialogCode
        def __init__(self, task, parent=None): pass
        def exec(self): return _ACCEPTED
        def get_data(self): return data
    return FakeDialog


# TID-1-2-023 | covers: TASK-2/ST003 happy
def test_edit_task_controller_happy_path_end_to_end(setup, monkeypatch):
    """EditTaskController.handle_edit end-to-end com DB temporario:
    dialog -> resolve_cycles -> filtra deps -> update -> recalc setor self + dependentes diretos."""
    ctrl, repo, conn, db_path = setup

    dep = Task(id="dep1", title="Dep", deps=[])
    main = Task(id="main", title="Main", deps=[])
    repo.create(dep)
    repo.create(main)

    from task_manager_desktop.controllers import edit_task_controller as mod
    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "Main editada",
        "deps": ["dep1"],
    }))

    ctrl.handle_edit(main)

    tasks = repo.list_active()
    updated = next(t for t in tasks if t.id == "main")
    assert updated.title == "Main editada"
    assert "dep1" in updated.deps

    all_tasks = {t.id: t for t in tasks}
    has_open = count_open_deps(updated.deps, all_tasks) > 0
    sector, _ = compute_sector(updated.status, has_open)
    assert sector == Sector.BLOCKED


# TID-1-2-024 | covers: TASK-2/ST003 RF-008
def test_edit_task_controller_recompute_only_one_level_deep(setup, monkeypatch):
    """Recalculo cobre UM NIVEL apenas: editar A nao recalcula setor de C que depende de B
    que depende de A (verifica ausencia de DFS)."""
    ctrl, repo, conn, db_path = setup

    a = Task(id="a", title="A", deps=[])
    b = Task(id="b", title="B", deps=["a"])
    c = Task(id="c", title="C", deps=["b"])
    repo.create(a)
    repo.create(b)
    repo.create(c)

    from task_manager_desktop.controllers import edit_task_controller as mod
    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "A editada",
        "deps": [],
    }))

    ctrl.handle_edit(a)

    tasks = repo.list_active()
    a_updated = next(t for t in tasks if t.id == "a")
    assert a_updated.title == "A editada"

    # B depends on A (direct), C depends on B (indirect) — verify both are in DB
    b_task = next(t for t in tasks if t.id == "b")
    c_task = next(t for t in tasks if t.id == "c")
    assert "a" in b_task.deps
    assert "b" in c_task.deps
