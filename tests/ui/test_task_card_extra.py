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
        type=TaskType.AGENT,
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
    # CL-079: faixa de selecao no lado ESQUERDO (border-left)
    assert "border-left: 3px solid #FFFFFF" in card.styleSheet()

    card.set_selected(False)
    assert card._selected is False
    assert "border-left: 3px solid #FFFFFF" not in card.styleSheet()


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
    task = _make_task(id="abc", title="Old", type=TaskType.AGENT, deps=[])
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)

    new = _make_task(id="xyz", title="New", type=TaskType.HUMAN, deps=[])
    card.update_task(new, [new])

    assert card._id_label.text() == "#xyz"
    assert card._title_label.text() == "New"
    assert not card._type_icon.pixmap().isNull()
    assert card._type_icon.toolTip() == "human"
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


# ----------------------------------------------------------------------
# Favorito autosave — lockout in-flight (source.md AC-14)
# ----------------------------------------------------------------------


def test_favorite_star_locked_during_in_flight_autosave(qtbot):
    """source.md AC-14: estrela em estado pending durante o autosave nao
    aceita novo toggle. Apos o request ser despachado a estrela esta
    desabilitada e um segundo toggle nao dispara um segundo autosave."""
    saves: list[bool] = []

    def on_favorite_toggle(task, value):
        saves.append(value)
        return True  # sucesso: na vida real dispara refresh; aqui so registra

    cbs = {"on_favorite_toggle": on_favorite_toggle}
    task = _make_task(id="fav", favorito=False)
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)

    # 1o toggle: marca pending, dispara o debounce (ainda sem request).
    card._star_btn.click()
    assert card._fav_in_flight is False
    assert card._star_btn.isEnabled() is True

    # Debounce dispara -> request despachado -> estrela travada in-flight.
    card._on_favorite_debounce_fired()
    assert card._fav_in_flight is True
    assert card._star_btn.isEnabled() is False
    assert saves == [True]  # exatamente um autosave

    # Tentativa de novo toggle durante o in-flight nao produz 2o autosave.
    card._on_star_toggled(False)
    assert saves == [True]
    # Click direto tambem e recusado (botao desabilitado).
    card._star_btn.click()
    assert saves == [True]


def test_favorite_star_reenabled_after_rollback(qtbot):
    """source.md AC-14: o lockout in-flight termina quando o request resolve.
    Em caso de falha (rollback), a estrela volta a aceitar toggles."""
    saves: list[bool] = []

    def on_favorite_toggle(task, value):
        saves.append(value)
        return False  # falha -> rollback

    cbs = {"on_favorite_toggle": on_favorite_toggle}
    task = _make_task(id="fav", favorito=False)
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)

    card._star_btn.click()
    card._on_favorite_debounce_fired()  # request falha -> rollback executado
    assert saves == [True]

    # Apos o rollback a estrela esta destravada e o foco de teclado preservado.
    assert card._fav_in_flight is False
    assert card._star_btn.isEnabled() is True
    assert card._star_btn.isChecked() is False  # revertido ao valor persistido

    # Novo toggle volta a ser aceito.
    card._star_btn.click()
    card._on_favorite_debounce_fired()
    assert saves == [True, True]


def test_favorite_rapid_clicks_coalesce_before_request(qtbot):
    """source.md secao 3.6: cliques rapidos dentro da janela de debounce (antes
    do request ser despachado) colapsam num unico autosave; ultimo valor vence.
    O lockout in-flight nao quebra esse coalescing pre-request."""
    saves: list[bool] = []

    def on_favorite_toggle(task, value):
        saves.append(value)
        return True

    cbs = {"on_favorite_toggle": on_favorite_toggle}
    task = _make_task(id="fav", favorito=False)
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)

    # 3 cliques rapidos antes do debounce disparar: nenhum request ainda.
    card._star_btn.click()  # -> True
    card._star_btn.click()  # -> False
    card._star_btn.click()  # -> True
    assert saves == []
    assert card._fav_in_flight is False
    assert card._fav_pending_value is True  # ultimo valor

    # Debounce dispara uma unica vez -> um unico autosave com o ultimo valor.
    card._on_favorite_debounce_fired()
    assert saves == [True]


def test_favorite_star_watchdog_rolls_back_when_request_never_resolves(qtbot, caplog):
    """source.md secao 9: se o callback de autosave nunca resolve (UI travada,
    lock no SQLite), o watchdog single-shot dispara, forca rollback ao valor
    persistido, re-habilita a estrela e loga um erro explicito com o task_id."""
    import logging

    # Callback que nunca retorna controle "limpo": simula stall deixando a
    # estrela travada in-flight (nao chamamos _rollback_star por aqui).
    cbs: dict = {}
    task = _make_task(id="stall", favorito=False)
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)

    # Forca o estado in-flight como se o request tivesse sido despachado e
    # nunca resolvido. Sem callback, _on_favorite_debounce_fired faria
    # rollback imediato; aqui isolamos so o lockout + watchdog.
    card._fav_pending_value = True
    with __import__("PySide6.QtCore", fromlist=["QSignalBlocker"]).QSignalBlocker(
        card._star_btn
    ):
        card._star_btn.setChecked(True)
    card._refresh_star_icon()
    card._set_star_pending(True)
    card._set_star_in_flight(True)

    assert card._fav_in_flight is True
    assert card._star_btn.isEnabled() is False
    assert card._fav_watchdog.isActive() is True

    # Dispara o watchdog manualmente (equivalente ao timeout single-shot).
    with caplog.at_level(logging.ERROR, logger="task_manager_desktop.ui.task_card"):
        card._on_favorite_watchdog_fired()

    # Estrela destravada e revertida ao valor persistido (favorito=False).
    assert card._fav_in_flight is False
    assert card._star_btn.isEnabled() is True
    assert card._star_btn.isChecked() is False
    assert card._fav_watchdog.isActive() is False

    # Erro explicito logado com o task_id.
    watchdog_logs = [
        rec.getMessage()
        for rec in caplog.records
        if "watchdog_timeout" in rec.getMessage()
    ]
    assert len(watchdog_logs) == 1
    assert "task_id=stall" in watchdog_logs[0]


def test_favorite_star_watchdog_stops_on_normal_resolution(qtbot):
    """O watchdog e armado quando o request e despachado e parado assim que
    ele resolve normalmente (rollback de falha), sem disparar rollback espurio."""
    saves: list[bool] = []

    def on_favorite_toggle(task, value):
        saves.append(value)
        return False  # falha -> rollback sincrono

    cbs = {"on_favorite_toggle": on_favorite_toggle}
    task = _make_task(id="fav", favorito=False)
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)

    card._star_btn.click()
    card._on_favorite_debounce_fired()  # request falha -> _rollback_star

    # Resolucao normal: o watchdog foi parado, nao ficou armado.
    assert card._fav_watchdog.isActive() is False
    assert card._fav_in_flight is False

    # Watchdog disparado apos a resolucao e inerte (guard de idempotencia).
    card._on_favorite_watchdog_fired()
    assert card._star_btn.isEnabled() is True
