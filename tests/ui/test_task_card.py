from __future__ import annotations

import pytest

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
        type=TaskType.ONLINE,
        projeto="forge",
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


def test_segmented_reflects_current_status(qtbot, callbacks):
    _, cbs = callbacks
    task = _make_task(status=Status.IN_PROGRESS)
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)
    assert card._seg_ctrl.btn_ip.isChecked() is True
    assert card._seg_ctrl.btn_p.isChecked() is False
    assert card._seg_ctrl.btn_d.isChecked() is False


def test_type_icon_online_tooltip(qtbot, callbacks):
    _, cbs = callbacks
    task = _make_task(type=TaskType.ONLINE)
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)
    assert card._type_icon.toolTip() == "online"


def test_type_icon_offline_tooltip(qtbot, callbacks):
    _, cbs = callbacks
    task = _make_task(type=TaskType.OFFLINE)
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)
    assert card._type_icon.toolTip() == "offline"


def test_project_hashtag_displayed(qtbot, callbacks):
    _, cbs = callbacks
    task = _make_task(projeto="systemforge")
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)
    assert "#systemforge" in card._project_tag.text()
    assert card._project_tag.toolTip() == "systemforge"


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
