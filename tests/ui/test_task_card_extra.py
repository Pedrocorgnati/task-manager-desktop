from __future__ import annotations

import pytest

from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.ui.task_card import TaskCard


@pytest.fixture
def calls_and_cbs():
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


def test_set_selected_toggles_style(qtbot, calls_and_cbs):
    _, cbs = calls_and_cbs
    task = _make_task()
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)
    assert card._selected is False

    card.set_selected(True)
    assert card._selected is True
    assert card.property("selected") is True
    assert "border-right" in card.styleSheet()

    card.set_selected(False)
    assert card._selected is False
    assert "border-right" not in card.styleSheet()


def test_on_status_change_invokes_callback(qtbot, calls_and_cbs):
    calls, cbs = calls_and_cbs
    task = _make_task()
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)

    card._on_status_change("done")
    assert calls["status"] == [("abc", "done")]


def test_on_status_change_no_callback_when_missing(qtbot):
    task = _make_task()
    card = TaskCard(task, {}, [task])
    qtbot.addWidget(card)
    # nao deve lancar
    card._on_status_change("done")


class _FakeAction:
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text


class _FakeMenu:
    """Stub usado pra evitar QMenu real (que trava em offscreen).
    Configurar _FakeMenu.return_index antes de instanciar (0=edit, 1=delete, None=dismiss)."""

    return_index = None

    def __init__(self, parent=None):
        self._actions = []

    def setStyleSheet(self, *a, **kw):
        pass

    def addAction(self, text):
        action = _FakeAction(text)
        self._actions.append(action)
        return action

    def actions(self):
        return list(self._actions)

    def exec(self, *args, **kwargs):
        if _FakeMenu.return_index is None:
            return None
        return self._actions[_FakeMenu.return_index]


@pytest.fixture
def fake_menu(monkeypatch):
    import task_manager_desktop.ui.task_card as task_card_mod
    monkeypatch.setattr(task_card_mod, "QMenu", _FakeMenu)
    yield _FakeMenu
    _FakeMenu.return_index = None


def test_show_context_menu_edit_branch(qtbot, calls_and_cbs, fake_menu):
    calls, cbs = calls_and_cbs
    task = _make_task()
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)

    fake_menu.return_index = 0
    card._show_context_menu()

    assert calls["edit"] == ["abc"]
    assert calls["delete"] == []


def test_show_context_menu_delete_branch(qtbot, calls_and_cbs, fake_menu):
    calls, cbs = calls_and_cbs
    task = _make_task()
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)

    fake_menu.return_index = 1
    card._show_context_menu()

    assert calls["delete"] == ["abc"]
    assert calls["edit"] == []


def test_show_context_menu_dismissed_returns_none(qtbot, calls_and_cbs, fake_menu):
    calls, cbs = calls_and_cbs
    task = _make_task()
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)

    fake_menu.return_index = None
    card._show_context_menu()

    assert calls["edit"] == []
    assert calls["delete"] == []


def test_update_task_changes_id_title_type_icon(qtbot, calls_and_cbs):
    _, cbs = calls_and_cbs
    task = _make_task(id="abc", title="Old", type=TaskType.ONLINE, deps=[])
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)

    new = _make_task(id="xyz", title="New", type=TaskType.OFFLINE, deps=[])
    card.update_task(new, [new])

    assert card._id_label.text() == "xyz"
    assert card._title_label.text() == "New"
    assert card._type_icon.toolTip() == "offline"
    assert card._deps_label.isHidden()


def test_update_task_shows_deps_label_when_deps_present(qtbot, calls_and_cbs):
    _, cbs = calls_and_cbs
    task = _make_task(id="main", deps=[])
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)
    card.show()
    assert card._deps_label.isHidden()

    dep = _make_task(id="dep1", status=Status.PENDING)
    new = _make_task(id="main", deps=["dep1"])
    card.update_task(new, [new, dep])

    assert not card._deps_label.isHidden()
    assert "dep1" in card._deps_label.text()


def test_pending_with_open_deps_uses_secondary_title_color(qtbot, calls_and_cbs):
    _, cbs = calls_and_cbs
    dep = _make_task(id="dep1", status=Status.PENDING)
    task = _make_task(id="main", status=Status.PENDING, deps=["dep1"])
    card = TaskCard(task, cbs, [task, dep])
    qtbot.addWidget(card)
    # pending_deps title color path: confirma que o styleSheet do title nao usa o TEXT_PRIMARY default
    from task_manager_desktop.ui.theme import PALETTE
    assert PALETTE["TEXT_SECONDARY"].lower() in card._title_label.styleSheet().lower()


def test_refresh_deps_label_uses_warning_color_when_open(qtbot, calls_and_cbs):
    _, cbs = calls_and_cbs
    dep = _make_task(id="dep1", status=Status.PENDING)
    task = _make_task(id="main", deps=["dep1"], status=Status.IN_PROGRESS)
    card = TaskCard(task, cbs, [task, dep])
    qtbot.addWidget(card)
    # warning color #eab308
    assert "#eab308" in card._deps_label.styleSheet().lower()


def test_refresh_deps_label_uses_neutral_color_when_all_closed(qtbot, calls_and_cbs):
    _, cbs = calls_and_cbs
    dep = _make_task(id="dep1", status=Status.DONE)
    task = _make_task(id="main", deps=["dep1"], status=Status.IN_PROGRESS)
    card = TaskCard(task, cbs, [task, dep])
    qtbot.addWidget(card)
    assert "#71717a" in card._deps_label.styleSheet().lower()
