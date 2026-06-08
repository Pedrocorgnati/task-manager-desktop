from __future__ import annotations

import pytest
from PySide6.QtCore import QUrl

from task_manager_desktop.core.models import Status, Task
from task_manager_desktop.ui.markdown_viewer import MarkdownViewer


def _make_task(**kwargs) -> Task:
    defaults = dict(
        id="1",
        title="A",
        status=Status.PENDING,
        deps=[],
        notes="",
        order_index=0,
    )
    defaults.update(kwargs)
    return Task(**defaults)


@pytest.fixture
def wired(qtbot):
    from task_manager_desktop.ui.task_list import TaskList

    task_list = TaskList()
    viewer = MarkdownViewer()
    qtbot.addWidget(task_list)
    qtbot.addWidget(viewer)
    # Wire-up: task_selected -> set_task (mirrors app.py logic via MarkdownReader)
    task_list.task_selected.connect(viewer.set_task)
    return task_list, viewer


def test_selection_drives_viewer_render(wired, qtbot):
    task_list, viewer = wired
    task = _make_task(notes="# A")
    task_list.task_selected.emit(task)
    assert not viewer._browser.isHidden()
    assert "A" in viewer._browser.toPlainText()


def test_deselection_drives_viewer_empty(wired, qtbot):
    task_list, viewer = wired
    task = _make_task(notes="# A")
    task_list.task_selected.emit(task)
    task_list.task_selected.emit(None)
    assert not viewer._empty.isHidden()
    assert "Selecione uma task" in viewer._empty._label.text()


def test_link_click_invokes_external_helper(qtbot, monkeypatch):
    import task_manager_desktop.ui.markdown_viewer as mv_mod

    calls: list[QUrl] = []
    monkeypatch.setattr(mv_mod, "_open_external_link", lambda url: calls.append(url) or True)
    viewer = MarkdownViewer()
    qtbot.addWidget(viewer)
    viewer._browser.anchorClicked.emit(QUrl("https://example.com"))
    assert calls and calls[0].toString() == "https://example.com"
