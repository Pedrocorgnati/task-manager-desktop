from __future__ import annotations

import sqlite3

import pytest

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Status, Subtask, Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui import subtask_pane as subtask_pane_mod
from task_manager_desktop.ui.subtask_pane import SubtaskClockPane, SubtaskPane

_ROLE_SUBTASK_ID = subtask_pane_mod._ROLE_SUBTASK_ID


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


def _ids(pane: SubtaskPane) -> list[str]:
    return [
        pane._list.item(i).data(_ROLE_SUBTASK_ID)
        for i in range(pane._list.count())
    ]


# ── Icone de tipo no card de subtask ────────────────────────────────────────


def test_subtask_card_renders_type_icon(qtbot, repo):
    repo.create(Task(id="a", title="A"))
    repo.create_subtask(Subtask(id="s0", task_id="a", text="S0", type=TaskType.HUMAN))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(repo.get_by_id("a"))

    row = pane._list.itemWidget(pane._list.item(0))
    assert row.type_icon.property("testid") == "subtask-type-icon-s0"
    assert not row.type_icon.pixmap().isNull()
    assert row.type_icon.toolTip() == "human"


def test_type_icon_click_cycles_to_next_type_and_persists(qtbot, repo):
    # Clicar no icone revezar agent -> human -> dev -> agent, persistindo cada
    # passo no repositorio e atualizando o glifo/tooltip in place.
    repo.create(Task(id="a", title="A"))
    repo.create_subtask(Subtask(id="s0", task_id="a", text="S0", type=TaskType.AGENT))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(repo.get_by_id("a"))
    row = pane._list.itemWidget(pane._list.item(0))

    row._on_type_icon_clicked(None)
    assert row._subtask.type is TaskType.HUMAN
    assert row.type_icon.toolTip() == "human"
    assert repo.list_subtasks("a")[0].type is TaskType.HUMAN

    row._on_type_icon_clicked(None)
    assert repo.list_subtasks("a")[0].type is TaskType.DEV

    row._on_type_icon_clicked(None)
    assert repo.list_subtasks("a")[0].type is TaskType.AGENT


def test_type_icon_click_ignored_in_compact_mode(qtbot, repo):
    repo.create(Task(id="a", title="A"))
    repo.create_subtask(Subtask(id="s0", task_id="a", text="S0", type=TaskType.AGENT))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(repo.get_by_id("a"))
    row = pane._list.itemWidget(pane._list.item(0))
    row.set_compact(True)

    row._on_type_icon_clicked(None)
    assert row._subtask.type is TaskType.AGENT
    assert repo.list_subtasks("a")[0].type is TaskType.AGENT


def test_type_icon_cycle_reverts_on_persist_failure(qtbot, repo, monkeypatch):
    repo.create(Task(id="a", title="A"))
    repo.create_subtask(Subtask(id="s0", task_id="a", text="S0", type=TaskType.AGENT))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(repo.get_by_id("a"))
    row = pane._list.itemWidget(pane._list.item(0))

    def boom(*_a, **_k):
        raise RuntimeError("io down")

    monkeypatch.setattr(repo, "update_subtask_type", boom)
    row._on_type_icon_clicked(None)

    # Modelo + icone voltam ao tipo anterior (rollback visual, sem dado gravado).
    assert row._subtask.type is TaskType.AGENT
    assert row.type_icon.toolTip() == "agent"


def test_type_icon_hidden_in_compact_mode(qtbot, repo):
    repo.create(Task(id="a", title="A"))
    repo.create_subtask(Subtask(id="s0", task_id="a", text="S0"))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(repo.get_by_id("a"))
    row = pane._list.itemWidget(pane._list.item(0))

    assert not row.type_icon.isHidden()
    row.set_compact(True)
    assert row.type_icon.isHidden()
    row.set_compact(False)
    assert not row.type_icon.isHidden()


# ── Filtro de tipo (header-type-filter) aplicado as subtasks ────────────────


def test_type_filter_hides_non_matching_subtasks_in_normal_mode(qtbot, repo):
    repo.create(Task(id="a", title="A"))
    repo.create_subtask(Subtask(id="ag", task_id="a", text="agent", type=TaskType.AGENT))
    repo.create_subtask(Subtask(id="dv", task_id="a", text="dev", type=TaskType.DEV))
    repo.create_subtask(Subtask(id="hu", task_id="a", text="human", type=TaskType.HUMAN))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(repo.get_by_id("a"))

    assert pane._list.count() == 3  # default: todos os tipos

    pane.set_type_filter(["agent"])
    assert _ids(pane) == ["ag"]

    pane.set_type_filter([TaskType.DEV, TaskType.HUMAN])
    assert _ids(pane) == ["dv", "hu"]


def test_type_filter_empty_shows_filtered_hint(qtbot, repo):
    repo.create(Task(id="a", title="A"))
    repo.create_subtask(Subtask(id="ag", task_id="a", text="agent", type=TaskType.AGENT))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(repo.get_by_id("a"))

    pane.set_type_filter(["dev"])  # nenhuma subtask dev
    assert pane._list.count() == 0
    assert pane._empty.isHidden() is False
    assert "filtrado" in pane._empty.text()


def test_type_filter_applies_in_show_all_mode(qtbot, repo):
    repo.create(Task(id="a", title="A", status=Status.IN_PROGRESS))
    repo.create(Task(id="b", title="B", status=Status.IN_PROGRESS))
    repo.create_subtask(Subtask(id="a_ag", task_id="a", text="A agent", type=TaskType.AGENT))
    repo.create_subtask(Subtask(id="b_dv", task_id="b", text="B dev", type=TaskType.DEV))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(repo.get_by_id("a"))

    pane.btn_show_all.setChecked(True)
    assert pane._list.count() == 2

    pane.set_type_filter(["dev"])
    assert _ids(pane) == ["b_dv"]


def test_set_type_filter_none_restores_all(qtbot, repo):
    repo.create(Task(id="a", title="A"))
    repo.create_subtask(Subtask(id="ag", task_id="a", text="agent", type=TaskType.AGENT))
    repo.create_subtask(Subtask(id="dv", task_id="a", text="dev", type=TaskType.DEV))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(repo.get_by_id("a"))

    pane.set_type_filter(["agent"])
    assert _ids(pane) == ["ag"]
    pane.set_type_filter(None)
    assert _ids(pane) == ["ag", "dv"]


def test_subtask_clock_pane_forwards_type_filter(qtbot, repo):
    pane = SubtaskClockPane(repo)
    qtbot.addWidget(pane)

    pane.set_type_filter(["dev"])
    assert pane.subtask_pane._task_types == frozenset({"dev"})


# ── Modal de criacao com radio de tipo (default agent) ──────────────────────


def test_prompt_new_subtask_defaults_to_agent(qtbot, repo, monkeypatch):
    from PySide6.QtWidgets import QDialog

    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    monkeypatch.setattr(QDialog, "exec", lambda self: int(QDialog.DialogCode.Accepted))

    assert pane._prompt_new_subtask(initial_text="nova") == ("nova", TaskType.AGENT)


def test_prompt_new_subtask_honours_initial_type(qtbot, repo, monkeypatch):
    from PySide6.QtWidgets import QDialog

    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    monkeypatch.setattr(QDialog, "exec", lambda self: int(QDialog.DialogCode.Accepted))

    assert pane._prompt_new_subtask(
        initial_text="x", initial_type=TaskType.DEV
    ) == ("x", TaskType.DEV)


def test_prompt_new_subtask_cancel_returns_none(qtbot, repo, monkeypatch):
    from PySide6.QtWidgets import QDialog

    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    monkeypatch.setattr(QDialog, "exec", lambda self: int(QDialog.DialogCode.Rejected))

    assert pane._prompt_new_subtask(initial_text="x") is None


def test_add_subtask_persists_chosen_type(qtbot, repo, monkeypatch):
    task = Task(id="a", title="A")
    repo.create(task)
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task)

    monkeypatch.setattr(
        pane, "_prompt_new_subtask", lambda *a, **k: ("nova dev", TaskType.DEV)
    )
    pane._add_subtask()

    subs = repo.list_subtasks("a")
    assert len(subs) == 1
    assert subs[0].text == "nova dev"
    assert subs[0].type is TaskType.DEV


# ── Hook on_subtasks_changed (reavalia filtro de cards principais) ───────────


def test_on_subtasks_changed_fires_on_add(qtbot, repo, monkeypatch):
    task = Task(id="a", title="A")
    repo.create(task)
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task)

    calls = []
    pane.set_on_subtasks_changed(lambda: calls.append("changed"))
    monkeypatch.setattr(pane, "_prompt_new_subtask", lambda *a, **k: ("x", TaskType.AGENT))
    pane._add_subtask()

    assert calls == ["changed"]


def test_on_subtasks_changed_fires_on_clear_done(qtbot, repo):
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="s0", task_id="a", text="done", state=2))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task)

    calls = []
    pane.set_on_subtasks_changed(lambda: calls.append("changed"))
    pane._clear_done_subtasks()

    assert calls == ["changed"]


def test_subtask_clock_pane_forwards_on_subtasks_changed(qtbot, repo):
    pane = SubtaskClockPane(repo)
    qtbot.addWidget(pane)

    sentinel = object()
    pane.set_on_subtasks_changed(sentinel)  # type: ignore[arg-type]
    assert pane.subtask_pane._on_subtasks_changed is sentinel


def test_clear_done_under_type_filter_keeps_hidden_type_done(qtbot, repo):
    # Filtro "agent" ativo: limpar concluidas nao pode apagar a subtask dev
    # concluida que esta OCULTA na view (anti perda de dados silenciosa).
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="ag", task_id="a", text="agent done", state=2, type=TaskType.AGENT))
    repo.create_subtask(Subtask(id="dv", task_id="a", text="dev done", state=2, type=TaskType.DEV))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task)
    pane.set_type_filter(["agent"])

    pane._clear_done_subtasks()

    remaining = {s.id for s in repo.list_subtasks("a")}
    assert remaining == {"dv"}


def test_dnd_disabled_under_active_type_filter(qtbot, repo):
    from PySide6.QtWidgets import QAbstractItemView

    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="s0", task_id="a", text="s", type=TaskType.AGENT))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task)

    # Sem filtro: DnD interno habilitado.
    assert pane._list.dragDropMode() == QAbstractItemView.DragDropMode.InternalMove
    # Filtro ativo: DnD desabilitado (reordenar sobre lista parcial e ambiguo).
    pane.set_type_filter(["agent"])
    assert pane._list.dragDropMode() == QAbstractItemView.DragDropMode.NoDragDrop


def test_add_subtask_order_index_skips_hidden_filtered(qtbot, repo, monkeypatch):
    # Sob filtro agent (1 subtask visivel) + 1 dev oculta, a nova subtask agent
    # deve receber order_index = max+1 = 3, nao count_visivel+1 = 2 (colisao).
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="ag", task_id="a", text="a", order_index=1, type=TaskType.AGENT))
    repo.create_subtask(Subtask(id="dv", task_id="a", text="d", order_index=2, type=TaskType.DEV))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task)
    pane.set_type_filter(["agent"])

    monkeypatch.setattr(pane, "_prompt_new_subtask", lambda *a, **k: ("nova", TaskType.AGENT))
    pane._add_subtask()

    new = next(s for s in repo.list_subtasks("a") if s.text == "nova")
    assert new.order_index == 3
