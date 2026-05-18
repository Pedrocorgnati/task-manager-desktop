from __future__ import annotations

import time

import pytest
from PySide6.QtCore import QUrl

from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.ui.markdown_viewer import MarkdownViewer


def _make_task(**kwargs) -> Task:
    defaults = dict(
        id="1",
        title="Test",
        status=Status.PENDING,
        type=TaskType.ONLINE,
        projeto="outros",
        deps=[],
        notes="",
        order_index=0,
    )
    defaults.update(kwargs)
    return Task(**defaults)


@pytest.fixture
def viewer(qtbot):
    w = MarkdownViewer()
    qtbot.addWidget(w)
    return w


def test_initial_state_shows_no_selection_empty(viewer):
    assert not viewer._empty.isHidden()
    assert viewer._browser.isHidden()
    assert "Selecione uma task" in viewer._empty._label.text()


def test_set_task_with_notes_renders_browser(viewer):
    task = _make_task(notes="# Hello\n\n- item1\n- item2")
    viewer.set_task(task)
    assert not viewer._browser.isHidden()
    assert viewer._empty.isHidden()
    assert "Hello" in viewer._browser.toPlainText()


def test_set_task_empty_notes_shows_no_notes_empty(viewer):
    task = _make_task(notes="")
    viewer.set_task(task)
    assert not viewer._empty.isHidden()
    assert "Sem notas ainda" in viewer._empty._label.text()


def test_set_task_none_returns_to_no_selection(viewer):
    task = _make_task(notes="# x")
    viewer.set_task(task)
    viewer.set_task(None)
    assert not viewer._empty.isHidden()
    assert "Selecione uma task" in viewer._empty._label.text()


def test_anchor_click_emits_link_clicked(viewer, qtbot, monkeypatch):
    import task_manager_desktop.ui.markdown_viewer as mv_mod

    monkeypatch.setattr(mv_mod, "_open_external_link", lambda url: True)
    with qtbot.waitSignal(viewer.link_clicked, timeout=500) as sig:
        viewer._browser.anchorClicked.emit(QUrl("https://example.com"))
    assert sig.args[0].toString() == "https://example.com"


def test_render_under_50ms_for_5kb(viewer):
    notes = "# Title\n\n" + ("Lorem ipsum dolor sit amet. " * 200)
    task = _make_task(notes=notes)
    t0 = time.perf_counter()
    viewer.set_task(task)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms <= 50, f"Render levou {elapsed_ms:.2f}ms"
