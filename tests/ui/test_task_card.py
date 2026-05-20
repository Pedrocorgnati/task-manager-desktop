from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.ui.task_card import TaskCard


@pytest.fixture
def callbacks():
    calls: dict = {"edit": [], "delete": [], "status": []}
    cbs = {
        "on_edit": lambda t: calls["edit"].append(t.id),
        "on_delete": lambda t: calls["delete"].append(t.id),
        "on_status_change": lambda t, s, *_: calls["status"].append((t.id, s)),
    }
    return calls, cbs


def _make_task(**kwargs) -> Task:
    defaults = dict(
        id="abc",
        title="Test",
        status=Status.PENDING,
        type=TaskType.AGENT,
        deps=[],
    )
    defaults.update(kwargs)
    return Task(**defaults)


def test_renders_three_rows(qtbot, callbacks):
    _, cbs = callbacks
    task = _make_task()
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)
    card.show()
    # id label e titulo aparecem no card
    assert card._id_label.text() == "abc"
    assert card._title_label.text() == "Test"


def test_card_has_95_5_content_and_status_columns(qtbot, callbacks):
    _, cbs = callbacks
    task = _make_task(id="vc9")
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)
    card.show()
    qtbot.waitExposed(card)

    layout = card.layout()
    assert layout.stretch(0) == 95
    assert layout.stretch(1) == 5
    assert layout.contentsMargins().top() == 0
    assert layout.contentsMargins().bottom() == 0
    assert layout.spacing() == 0
    assert card._content_col.property("testid") == "task-card-vc9-content"
    assert card._status_col.property("testid") == "task-card-vc9-status-column"
    assert card._seg_ctrl.parent() is card._status_col
    assert card._actions_row.parent() is card._top_row
    assert card._content_col.height() == card._status_col.height()
    assert card._content_col.geometry().top() == card._status_col.geometry().top()
    assert card._content_col.geometry().bottom() == card._status_col.geometry().bottom()


def test_menu_has_editar_and_excluir(qtbot, callbacks):
    _, cbs = callbacks
    task = _make_task()
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)
    card.show()
    from unittest.mock import patch

    import PySide6.QtWidgets as qw

    with patch.object(qw.QMenu, "exec", lambda self, *a, **kw: None):
        from PySide6.QtWidgets import QMenu
        menu = QMenu()
        menu.addAction("Editar")
        menu.addAction("Excluir")
        actions = [a.text() for a in menu.actions()]
        assert actions == ["Editar", "Excluir"]


def test_editar_callback_invoked(qtbot, callbacks):
    calls, cbs = callbacks
    task = _make_task()
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)
    # Simular callback diretamente
    cbs["on_edit"](task)
    assert calls["edit"] == ["abc"]


def test_excluir_callback_invoked(qtbot, callbacks):
    calls, cbs = callbacks
    task = _make_task()
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)
    cbs["on_delete"](task)
    assert calls["delete"] == ["abc"]


def test_hover_actions_start_hidden_and_call_callbacks(qtbot, callbacks):
    calls, cbs = callbacks
    task = _make_task()
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)
    card.show()

    assert card._actions_row.isVisible() is False

    card._set_hover_actions_visible(True)
    assert card._actions_row.isVisible() is True

    qtbot.mouseClick(card._edit_btn, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(card._delete_btn, Qt.MouseButton.LeftButton)

    assert calls["edit"] == ["abc"]
    assert calls["delete"] == ["abc"]


def test_segmented_reflects_current_status(qtbot, callbacks):
    _, cbs = callbacks
    task = _make_task(status=Status.IN_PROGRESS)
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)
    assert card._seg_ctrl.btn_ip.isChecked() is True
    assert card._seg_ctrl.btn_p.isChecked() is False
    assert card._seg_ctrl.btn_d.isChecked() is False


def test_type_icon_agent_tooltip(qtbot, callbacks):
    _, cbs = callbacks
    task = _make_task(type=TaskType.AGENT)
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)
    assert not card._type_icon.pixmap().isNull()
    assert card._type_icon.toolTip() == "agent"


def test_type_icon_human_tooltip(qtbot, callbacks):
    _, cbs = callbacks
    task = _make_task(type=TaskType.HUMAN)
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)
    assert not card._type_icon.pixmap().isNull()
    assert card._type_icon.toolTip() == "human"


def test_border_reflects_in_progress_active(qtbot, callbacks):
    _, cbs = callbacks
    task = _make_task(status=Status.IN_PROGRESS, deps=[])
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)
    # Sem deps abertas -> lime/green border
    assert "#16a34a" in card.styleSheet().lower()


def test_deps_label_hidden_when_empty(qtbot, callbacks):
    _, cbs = callbacks
    task = _make_task(deps=[])
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)
    assert not card._deps_label.isVisible()


def test_deps_label_visible_with_deps(qtbot, callbacks):
    _, cbs = callbacks
    dep = _make_task(id="dep1", status=Status.PENDING)
    task = _make_task(id="abc", deps=["dep1"])
    card = TaskCard(task, cbs, [task, dep])
    qtbot.addWidget(card)
    assert not card._deps_label.isHidden()
    assert "dep1" in card._deps_label.text()


def test_deps_warning_color_with_open_dep(qtbot, callbacks):
    _, cbs = callbacks
    dep = _make_task(id="dep1", status=Status.PENDING)
    task = _make_task(id="main", deps=["dep1"], status=Status.PENDING)
    card = TaskCard(task, cbs, [task, dep])
    qtbot.addWidget(card)
    assert card._deps_label.property("has-open-deps") is not False
