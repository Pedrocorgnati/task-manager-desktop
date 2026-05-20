from __future__ import annotations

import sqlite3

import pytest
from PySide6.QtCore import Qt

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Subtask, Task
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.subtask_pane import SubtaskPane


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    run_migrations(c)
    yield c
    c.close()


@pytest.fixture
def repo(conn):
    return TaskRepository(conn, db_path=":memory:")


def test_clear_done_button_is_disabled_without_completed_subtasks(qtbot, repo):
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="A0", state=0))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)

    pane.set_task(task)

    assert not pane.btn_clear_done.isEnabled()
    assert "Nenhuma subtask concluída" in pane.btn_clear_done.toolTip()


def test_clear_done_button_deletes_only_selected_task_completed_subtasks(qtbot, repo):
    task_a = Task(id="a", title="A")
    task_b = Task(id="b", title="B")
    repo.create(task_a)
    repo.create(task_b)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="A0", state=0))
    repo.create_subtask(Subtask(id="a2", task_id="a", text="A2", state=2))
    repo.create_subtask(Subtask(id="b2", task_id="b", text="B2", state=2))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task_a)

    assert pane.btn_clear_done.isEnabled()
    qtbot.mouseClick(pane.btn_clear_done, Qt.MouseButton.LeftButton)

    assert [s.id for s in repo.list_subtasks("a")] == ["a0"]
    assert [s.id for s in repo.list_subtasks("b")] == ["b2"]
    assert not pane.btn_clear_done.isEnabled()


def test_subtask_notes_chevron_visibility_and_autosave(qtbot, repo):
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="A0", state=0))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task)

    item = pane._list.item(0)
    row = pane._list.itemWidget(item)
    assert row.notes_toggle.isHidden() is True

    row.enterEvent(None)
    assert row.notes_toggle.isHidden() is False
    assert row.notes_toggle.property("hasNotes") is False

    qtbot.mouseClick(row.notes_toggle, Qt.MouseButton.LeftButton)
    assert row.notes_editor.isHidden() is False
    assert item.sizeHint().height() > 38

    row.notes_editor.setPlainText("nota salva")
    assert repo.list_subtasks("a")[0].notes == "nota salva"

    qtbot.mouseClick(row.notes_toggle, Qt.MouseButton.LeftButton)
    row.leaveEvent(None)
    assert row.notes_editor.isHidden() is True
    assert row.notes_toggle.isHidden() is False
    assert row.notes_toggle.property("hasNotes") is True
    assert "#111116" in row.notes_toggle.styleSheet()


def test_subtask_with_existing_notes_shows_strong_chevron_without_hover(qtbot, repo):
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="A0", state=0, notes="detalhe"))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task)

    row = pane._list.itemWidget(pane._list.item(0))

    assert row.notes_toggle.isHidden() is False
    assert row.notes_toggle.property("hasNotes") is True
    assert "#111116" in row.notes_toggle.styleSheet()


def test_subtask_inline_edit_autosaves_on_finish(qtbot, repo):
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="original", state=0))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task)

    row = pane._list.itemWidget(pane._list.item(0))
    row._begin_inline_edit()
    row._inline_edit.setText("alterado")
    row._commit_inline_edit()

    assert repo.list_subtasks("a")[0].text == "alterado"


def test_subtask_pane_width_is_stable_with_or_without_subtasks(qtbot, repo):
    empty_task = Task(id="empty", title="Empty")
    filled_task = Task(id="filled", title="Filled")
    repo.create(empty_task)
    repo.create(filled_task)
    repo.create_subtask(
        Subtask(
            id="s-long",
            task_id="filled",
            text="Subtask com texto longo suficiente para quebrar linha sem mudar largura",
            state=0,
        )
    )
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)

    pane.set_task(empty_task)
    empty_width = (pane.minimumWidth(), pane.maximumWidth())

    pane.set_task(filled_task)

    assert pane.property("testid") == "subtask-pane"
    assert (pane.minimumWidth(), pane.maximumWidth()) == empty_width


def test_subtask_title_renders_in_body_before_cards(qtbot, repo):
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="A0", state=0))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)

    pane.set_task(task)

    assert pane._body_title.property("testid") == "subtask-pane-title"
    assert pane._body_title.text() == "Subtasks #a"
    assert pane._layout.indexOf(pane._body_title) < pane._layout.indexOf(pane._list)
    assert pane._header_layout.indexOf(pane._body_title) == -1


def test_subtask_card_width_is_reduced_inside_fixed_pane(qtbot, repo):
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="A0", state=0))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)

    pane.set_task(task)

    row = pane._list.itemWidget(pane._list.item(0))
    assert row._card.width() == row._card.minimumWidth()
    assert row._card.maximumWidth() == row._card.minimumWidth()
    assert row._card.width() < pane.width()
