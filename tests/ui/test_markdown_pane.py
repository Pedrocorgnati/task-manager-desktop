from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.ui.markdown_pane import MarkdownPane


def _make_task(task_id: str = "t1", notes: str = "# Nota") -> Task:
    return Task(
        id=task_id,
        title=f"Task {task_id}",
        status=Status.PENDING,
        type=TaskType.AGENT,
        deps=[],
        notes=notes,
        order_index=0,
    )


@pytest.fixture
def pane(qtbot):
    w = MarkdownPane()
    qtbot.addWidget(w)
    return w


@pytest.fixture
def sample_task() -> Task:
    return _make_task("ta", "# Original")


@pytest.fixture
def sample_task_b() -> Task:
    return _make_task("tb", "# Nota B")


# ── Estrutura inicial ─────────────────────────────────────────────────────────


def test_initial_stack_shows_viewer(pane):
    assert pane.stack.currentIndex() == 0


def test_btn_edit_hidden_when_no_task(pane):
    pane.set_task(None)
    assert not pane.btn_edit.isVisible()


def test_btn_edit_visible_after_set_task(pane, sample_task):
    pane.set_task(sample_task)
    assert not pane.btn_edit.isVisibleTo(pane)
    assert pane.toolbar.btn_save.isEnabled()
    assert pane.toolbar.btn_toggle.isEnabled()


# ── Transição viewer → editor ────────────────────────────────────────────────


def test_edit_button_switches_to_editor(qtbot, pane, sample_task):
    pane.show()
    with qtbot.waitSignal(pane.editing_changed) as blocker:
        pane.set_task(sample_task)
    assert blocker.args == [True]
    assert pane.stack.currentIndex() == 1
    assert pane.editor.toPlainText() == sample_task.notes
    pane.hide()


# ── Cancel descarta e volta ao viewer ────────────────────────────────────────


def test_cancel_returns_to_viewer_with_original(qtbot, pane, sample_task):
    pane.show()
    pane.set_task(sample_task)
    pane.editor.setPlainText("# modificado")
    with qtbot.waitSignal(pane.editing_changed) as blocker:
        pane.toolbar.cancel_requested.emit()
    assert blocker.args == [False]
    assert pane.stack.currentIndex() == 0
    pane.toolbar.toggle_preview_requested.emit()
    assert pane.editor.toPlainText() == sample_task.notes
    pane.hide()


# ── set_task reseta para viewer ───────────────────────────────────────────────


def test_set_task_resets_to_viewer(qtbot, pane, sample_task, sample_task_b):
    pane.show()
    pane.set_task(sample_task)
    assert pane.stack.currentIndex() == 1
    pane.set_task(sample_task_b)
    assert pane.stack.currentIndex() == 1
    pane.hide()


def test_set_task_none_hides_edit_button(pane, sample_task):
    pane.set_task(sample_task)
    assert not pane.btn_edit.isVisibleTo(pane)
    pane.set_task(None)
    assert not pane.btn_edit.isVisibleTo(pane)


# ── editing_changed emitido em toda transição ─────────────────────────────────


def test_editing_changed_emitted_true_on_edit(qtbot, pane, sample_task):
    pane.show()
    signals = []
    pane.editing_changed.connect(signals.append)
    pane.set_task(sample_task)
    assert signals == [True]
    pane.hide()


def test_editing_changed_emitted_false_on_cancel(qtbot, pane, sample_task):
    pane.show()
    pane.set_task(sample_task)
    signals = []
    pane.editing_changed.connect(signals.append)
    pane.toolbar.cancel_requested.emit()
    assert signals == [False]
    pane.hide()


def test_reader_theme_toggle_changes_editor_palette(qtbot, pane, sample_task):
    pane.show()
    pane.set_task(sample_task)
    assert pane.reader_light_mode() is False
    pane.toolbar.btn_reader_theme.click()
    assert pane.reader_light_mode() is True
    assert pane.editor.palette().base().color().name().lower() == "#fafaf7"
    assert pane.editor.palette().text().color().name().lower() == "#111116"
    pane.toolbar.btn_reader_theme.click()
    assert pane.reader_light_mode() is False
    assert pane.editor.palette().base().color().name().lower() == "#0d0e12"
    pane.hide()
