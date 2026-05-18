from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QLineEdit, QMainWindow, QPlainTextEdit

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.shortcuts_controller import (
    _SHORTCUT_MAP,
    _SUPPRESS_IN_TEXT,
    ShortcutsController,
)
from task_manager_desktop.ui.task_list import _ROLE_TYPE, TaskList


@pytest.fixture
def repo(in_memory_db):
    run_migrations(in_memory_db)
    return TaskRepository(in_memory_db, db_path=":memory:")


def _mk(tid: str, *, status: Status = Status.PENDING, order_index: int = 0) -> Task:
    return Task(
        id=tid,
        title=f"task-{tid}",
        status=status,
        type=TaskType.OFFLINE,
        projeto="alpha",
        deps=[],
        notes="",
        order_index=order_index,
        created_at="2026-05-17T10:00:00",
    )


# ------------------------------------------------------------------
# TaskList selection helpers
# ------------------------------------------------------------------
def test_select_next_skips_separators(qtbot, repo):
    repo.create(_mk("a", status=Status.PENDING))
    repo.create(_mk("b", status=Status.PENDING, order_index=1))
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl._inner.setCurrentRow(0)
    assert tl._inner.item(0).data(_ROLE_TYPE) == "separator"

    tl.select_next()
    cur = tl._inner.currentRow()
    assert tl._inner.item(cur).data(_ROLE_TYPE) == "task"


def test_select_prev_stays_on_first_task(qtbot, repo):
    repo.create(_mk("a", status=Status.PENDING))
    repo.create(_mk("b", status=Status.PENDING, order_index=1))
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.select_next()
    first_task_row = tl._inner.currentRow()
    tl.select_prev()
    assert tl._inner.currentRow() == first_task_row


def test_select_next_stops_on_last_task(qtbot, repo):
    repo.create(_mk("a", status=Status.PENDING))
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.select_next()
    last = tl._inner.currentRow()
    tl.select_next()
    assert tl._inner.currentRow() == last


def test_get_selected_task_returns_none_for_separator(qtbot, repo):
    repo.create(_mk("a", status=Status.PENDING))
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl._inner.setCurrentRow(0)
    assert tl.get_selected_task() is None


def test_get_selected_task_returns_task(qtbot, repo):
    repo.create(_mk("a", status=Status.PENDING))
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.select_next()
    got = tl.get_selected_task()
    assert got is not None
    assert got.id == "a"


def test_open_selected_emits_task_selected(qtbot, repo):
    repo.create(_mk("a", status=Status.PENDING))
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())
    tl.select_next()

    with qtbot.waitSignal(tl.task_selected, timeout=300) as blocker:
        tl.open_selected()
    assert blocker.args[0].id == "a"


def test_open_selected_noop_without_selection(qtbot, repo):
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh([])
    tl.open_selected()  # must not raise, must not emit


# ------------------------------------------------------------------
# ShortcutsController
# ------------------------------------------------------------------
def test_controller_registers_all_shortcuts(qtbot):
    win = QMainWindow()
    qtbot.addWidget(win)
    sc = ShortcutsController(win, {})
    sc.install()

    sequences = {
        s.key().toString() for s in win.findChildren(QShortcut)
    }
    for key in _SHORTCUT_MAP.keys():
        assert QKeySequence(key).toString() in sequences


def test_controller_fires_callback_directly(qtbot):
    win = QMainWindow()
    qtbot.addWidget(win)

    called: list[str] = []
    cbs = {
        "edit_selected": lambda: called.append("edit"),
        "focus_search": lambda: called.append("focus"),
        "delete_selected": lambda: called.append("delete"),
    }
    sc = ShortcutsController(win, cbs)
    sc.install()

    # Invoke via the controller's wrapped slots (offscreen can't deliver keystrokes
    # reliably; we exercise the wrap+dispatch path directly).
    for s in sc._shortcuts:
        if s.key() == QKeySequence("Ctrl+E"):
            s.activated.emit()
        elif s.key() == QKeySequence("Ctrl+F"):
            s.activated.emit()

    assert "edit" in called
    assert "focus" in called


def test_controller_suppresses_destructive_when_focus_is_text(qtbot):
    win = QMainWindow()
    qtbot.addWidget(win)
    editor = QPlainTextEdit(win)
    win.setCentralWidget(editor)
    win.show()
    qtbot.waitExposed(win)
    editor.setFocus()

    called: list[str] = []
    sc = ShortcutsController(
        win,
        {
            "delete_selected": lambda: called.append("delete"),
            "focus_search": lambda: called.append("focus"),
        },
    )
    sc.install()

    # Force focus to editor
    editor.setFocus()
    qtbot.wait(20)

    for s in sc._shortcuts:
        if s.key() == QKeySequence("Delete"):
            s.activated.emit()
        elif s.key() == QKeySequence("Ctrl+F"):
            s.activated.emit()

    # delete must be suppressed; focus_search must NOT be suppressed
    assert "delete" not in called
    assert "focus" in called


def test_suppression_set_matches_spec():
    expected = {
        "delete_selected",
        "select_prev",
        "select_next",
        "open_selected",
        "edit_selected",
        "mark_done_selected",
    }
    assert _SUPPRESS_IN_TEXT == expected


def test_qlineedit_focus_also_suppresses_destructive(qtbot):
    win = QMainWindow()
    qtbot.addWidget(win)
    le = QLineEdit(win)
    win.setCentralWidget(le)
    win.show()
    qtbot.waitExposed(win)
    le.setFocus()

    called: list[str] = []
    sc = ShortcutsController(
        win,
        {"delete_selected": lambda: called.append("delete")},
    )
    sc.install()
    qtbot.wait(20)

    for s in sc._shortcuts:
        if s.key() == QKeySequence("Delete"):
            s.activated.emit()

    assert called == []


def test_missing_callback_does_not_raise(qtbot):
    win = QMainWindow()
    qtbot.addWidget(win)
    sc = ShortcutsController(win, {})
    sc.install()

    for s in sc._shortcuts:
        if s.key() == QKeySequence("Ctrl+E"):
            s.activated.emit()  # no callback registered — should be silent
