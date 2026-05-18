from __future__ import annotations

import pytest
from PySide6.QtWidgets import QFrame, QLabel, QPushButton

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.dialogs.trash_dialog import TrashDialog


@pytest.fixture
def repo(in_memory_db):
    run_migrations(in_memory_db)
    return TaskRepository(in_memory_db, db_path=":memory:")


def _seed_done(
    repo: TaskRepository,
    tid: str,
    title: str = "T",
    completed_at: str = "2026-05-17T11:30:00",
) -> None:
    repo.create(
        Task(
            id=tid,
            title=title,
            status=Status.DONE,
            type=TaskType.OFFLINE,
            projeto="alpha",
            deps=[],
            notes="",
            order_index=0,
            created_at="2026-05-17T10:00:00",
        )
    )
    repo.update(tid, completed_at=completed_at)


def test_trash_dialog_empty_state(qtbot, repo):
    dlg = TrashDialog(repo)
    qtbot.addWidget(dlg)
    placeholder = dlg.findChild(QLabel, "trashEmptyPlaceholder")
    assert placeholder is not None
    assert placeholder.isVisibleTo(dlg) or dlg._stack.currentIndex() == 0
    assert dlg.row_ids() == []


def test_trash_dialog_lists_hidden_rows(qtbot, repo):
    _seed_done(repo, "a", title="Task A")
    _seed_done(repo, "b", title="Task B")
    repo.hide_all_done()

    dlg = TrashDialog(repo)
    qtbot.addWidget(dlg)

    rows = dlg.findChildren(QFrame, "trashRow")
    assert len(rows) == 2
    assert set(dlg.row_ids()) == {"a", "b"}


def test_trash_dialog_row_shows_id_title_and_date(qtbot, repo):
    _seed_done(repo, "abc", title="Refactor header")
    repo.hide_all_done()

    dlg = TrashDialog(repo)
    qtbot.addWidget(dlg)

    id_labels = dlg.findChildren(QLabel, "trashRowId")
    title_labels = dlg.findChildren(QLabel, "trashRowTitle")
    date_labels = dlg.findChildren(QLabel, "trashRowDate")

    assert any(lbl.text() == "abc" for lbl in id_labels)
    assert any("Refactor header" in lbl.text() for lbl in title_labels)
    assert any("2026-05-17" in lbl.text() for lbl in date_labels)


def test_trash_dialog_restore_removes_row_and_calls_repo(qtbot, repo):
    _seed_done(repo, "a")
    repo.hide_all_done()

    dlg = TrashDialog(repo)
    qtbot.addWidget(dlg)

    btn = dlg.findChild(QPushButton, "trashRowRestore")
    assert btn is not None

    with qtbot.waitSignal(dlg.restore_requested, timeout=500) as blocker:
        btn.click()

    assert blocker.args == ["a"]
    assert dlg.row_ids() == []
    assert repo.get_by_id("a").hidden_at is None


def test_trash_dialog_remove_row_switches_to_empty_state(qtbot, repo):
    _seed_done(repo, "a")
    repo.hide_all_done()

    dlg = TrashDialog(repo)
    qtbot.addWidget(dlg)

    assert dlg._stack.currentIndex() == 1
    dlg.remove_row("a")
    assert dlg._stack.currentIndex() == 0


def test_trash_dialog_reload_refreshes_rows(qtbot, repo):
    _seed_done(repo, "a")
    repo.hide_all_done()

    dlg = TrashDialog(repo)
    qtbot.addWidget(dlg)
    assert dlg.row_ids() == ["a"]

    _seed_done(repo, "b")
    repo.hide_all_done()
    dlg.reload()
    assert set(dlg.row_ids()) == {"a", "b"}
