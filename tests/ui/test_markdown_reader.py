from __future__ import annotations

import sqlite3

import pytest
from PySide6.QtCore import Qt

from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.markdown_reader import MarkdownReader


def _make_task(**kwargs) -> Task:
    defaults = dict(
        id="abc",
        title="Test",
        status=Status.PENDING,
        type=TaskType.ONLINE,
        projeto="forge",
        deps=[],
        notes="",
        order_index=0,
    )
    defaults.update(kwargs)
    return Task(**defaults)


@pytest.fixture
def repo(in_memory_db):
    from task_manager_desktop.core.db import run_migrations
    run_migrations(in_memory_db)
    return TaskRepository(in_memory_db, db_path=":memory:")


def test_show_task_sets_viewer_mode(qtbot):
    reader = MarkdownReader(repo=None)
    qtbot.addWidget(reader)
    task = _make_task(notes="# hello\n\nworld")
    reader.show_task(task)
    assert reader._stack.currentIndex() == MarkdownReader._IDX_VIEWER
    assert "hello" in reader._viewer.toPlainText()


def test_show_task_empty_notes_shows_placeholder(qtbot):
    reader = MarkdownReader(repo=None)
    qtbot.addWidget(reader)
    task = _make_task(notes="")
    reader.show_task(task)
    assert reader._stack.currentIndex() == MarkdownReader._IDX_VIEWER


def test_clear_returns_to_placeholder(qtbot):
    reader = MarkdownReader(repo=None)
    qtbot.addWidget(reader)
    reader.show_task(_make_task(notes="x"))
    reader.clear()
    assert reader._stack.currentIndex() == MarkdownReader._IDX_PLACEHOLDER
    assert reader.current_task_id() is None


def test_edit_then_cancel_discards_changes(qtbot):
    reader = MarkdownReader(repo=None)
    qtbot.addWidget(reader)
    reader.show_task(_make_task(notes="original"))
    reader._on_edit_clicked()
    assert reader._stack.currentIndex() == MarkdownReader._IDX_EDITOR
    reader._editor.setPlainText("dirty")
    reader._on_cancel_clicked()
    assert reader._stack.currentIndex() == MarkdownReader._IDX_VIEWER
    assert "original" in reader._viewer.toPlainText()


def test_save_persists_and_returns_to_viewer(qtbot, repo):
    task = _make_task(id="t1", notes="old")
    repo.create(task)
    reader = MarkdownReader(repo)
    qtbot.addWidget(reader)
    reader.show_task(task)
    reader._on_edit_clicked()
    reader._editor.setPlainText("new content")
    reader._on_save_clicked()
    assert reader._stack.currentIndex() == MarkdownReader._IDX_VIEWER
    assert repo.get_by_id("t1").notes == "new content"


def test_ctrl_s_saves(qtbot, repo):
    task = _make_task(id="t2", notes="old")
    repo.create(task)
    reader = MarkdownReader(repo)
    qtbot.addWidget(reader)
    reader.show()
    qtbot.waitExposed(reader)
    reader.show_task(task)
    reader._on_edit_clicked()
    reader._editor.setPlainText("via shortcut")
    reader._editor.setFocus()
    reader._save_shortcut.activated.emit()
    assert repo.get_by_id("t2").notes == "via shortcut"
    assert reader._stack.currentIndex() == MarkdownReader._IDX_VIEWER


def test_save_failure_keeps_editor_open(qtbot, repo, monkeypatch):
    task = _make_task(id="t3", notes="x")
    repo.create(task)
    reader = MarkdownReader(repo)
    qtbot.addWidget(reader)
    reader.show_task(task)
    reader._on_edit_clicked()
    reader._editor.setPlainText("xx")

    def _boom(*_a, **_kw):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(repo, "update_notes", _boom)
    # silenciar dialog
    monkeypatch.setattr(reader, "_show_io_error", lambda exc: None)
    reader._on_save_clicked()
    assert reader._stack.currentIndex() == MarkdownReader._IDX_EDITOR
    assert reader._editor.toPlainText() == "xx"


def test_show_task_during_edit_emits_switch_blocked(qtbot):
    reader = MarkdownReader(repo=None)
    qtbot.addWidget(reader)
    reader.show_task(_make_task(id="a", notes="a"))
    reader._on_edit_clicked()
    other = _make_task(id="b", notes="b")
    with qtbot.waitSignal(reader.switch_blocked, timeout=500):
        reader.show_task(other)
    # task atual NAO mudou
    assert reader.current_task_id() == "a"
    assert reader._stack.currentIndex() == MarkdownReader._IDX_EDITOR


def test_external_links_enabled(qtbot):
    reader = MarkdownReader(repo=None)
    qtbot.addWidget(reader)
    assert reader._viewer.openExternalLinks() is True


def test_show_same_task_twice_is_idempotent(qtbot):
    reader = MarkdownReader(repo=None)
    qtbot.addWidget(reader)
    task = _make_task(id="abc", notes="content")
    reader.show_task(task)
    reader._viewer.verticalScrollBar().setValue(0)
    reader.show_task(task)  # mesmo notes/id -> no re-render
    # Idempotente: ainda no viewer com o mesmo task
    assert reader.current_task_id() == "abc"
    assert reader._stack.currentIndex() == MarkdownReader._IDX_VIEWER
