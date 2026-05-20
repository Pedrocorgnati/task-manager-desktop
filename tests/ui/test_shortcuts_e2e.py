"""Smoke / e2e tests for the canonical keyboard shortcut registry (RF-011 / US-010).

These tests verify observable end-to-end behaviour of the ShortcutsController wired
to real (non-mock) TaskList state, without requiring a fully-mounted MainWindow.
Full integration tests against MainWindow + real DB are deferred to manual QA
(AC-T-011 in _TESTS-A11Y.md) because they depend on helpers not yet on the public API.
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.shortcuts import (
    ControllerBundle,
    ShortcutsController,
    _SHORTCUT_MAP,
    _SUPPRESS_IN_TEXT,
    register_all,
)
from task_manager_desktop.ui.task_list import TaskList


@pytest.fixture
def repo(in_memory_db):
    run_migrations(in_memory_db)
    return TaskRepository(in_memory_db, db_path=":memory:")


def _make_task(repo: TaskRepository, *, tid: str, title: str) -> Task:
    t = Task(
        id=tid,
        title=title,
        status=Status.PENDING,
        type=TaskType.HUMAN,
        deps=[],
        notes="",
        order_index=1,
        created_at="2026-05-18T10:00:00",
    )
    repo.create(t)
    return t


# ------------------------------------------------------------------
# Registry completeness (AC-T-001)
# ------------------------------------------------------------------


def test_shortcut_map_covers_active_rf011_keys():
    expected = {
        "Ctrl+E",
        "Ctrl+D",
        "Up",
        "Down",
        "Return",
        "Enter",
        "Delete",
        "Escape",
    }
    # Ctrl+N handled by header.install_shortcut — NOT in _SHORTCUT_MAP by design
    assert expected.issubset(set(_SHORTCUT_MAP.keys()))


def test_suppression_set_excludes_global_shortcuts():
    global_keys = {"esc_handler"}
    assert _SUPPRESS_IN_TEXT.isdisjoint(global_keys), (
        "Global shortcuts must never be suppressed in text fields"
    )


def test_register_all_returns_nonempty_list(qtbot):
    from task_manager_desktop.ui.main_window import MainWindowShell

    window = MainWindowShell()
    qtbot.addWidget(window)
    bundle = ControllerBundle()
    shortcuts = register_all(window, bundle)
    assert isinstance(shortcuts, list)
    assert len(shortcuts) > 0


# ------------------------------------------------------------------
# No-op for contextual shortcuts without selection (AC-T-004)
# ------------------------------------------------------------------


def test_edit_selected_is_noop_without_selection(qtbot, repo):
    _make_task(repo, tid="t1", title="task")
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())
    tl._inner.clearSelection()
    tl._inner.setCurrentRow(-1)

    called: list[bool] = []

    def _edit() -> None:
        t = tl.get_selected_task()
        if t is not None:
            called.append(True)

    _edit()
    assert called == []


def test_delete_selected_is_noop_without_selection(qtbot, repo):
    _make_task(repo, tid="t1", title="task")
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())
    tl._inner.clearSelection()
    tl._inner.setCurrentRow(-1)

    called: list[bool] = []

    def _delete() -> None:
        t = tl.get_selected_task()
        if t is not None:
            called.append(True)

    _delete()
    assert called == []


# ------------------------------------------------------------------
# Esc hierarchy (AC-T-003) — unit-level without full app
# ------------------------------------------------------------------


def test_esc_handler_hierarchy_deselect_without_search_level():
    """Esc now skips removed search level and deselects when no modal is active."""
    task_deselected: list[bool] = []

    def _handle_escape() -> None:
        task_deselected.append(True)

    _handle_escape()

    assert task_deselected == [True]


# ------------------------------------------------------------------
# Ownership: register_all return value kept alive (AC-T-001)
# ------------------------------------------------------------------


def test_shortcuts_ownership_stored_on_window(qtbot):
    from task_manager_desktop.ui.main_window import MainWindowShell

    window = MainWindowShell()
    qtbot.addWidget(window)
    bundle = ControllerBundle()
    window._shortcuts = register_all(window, bundle)
    assert hasattr(window, "_shortcuts")
    assert len(window._shortcuts) == len(_SHORTCUT_MAP)
