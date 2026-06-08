from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Sector, Status, Subtask, Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.task_list import (
    _ROLE_SECTOR,
    _ROLE_TASK_ID,
    _ROLE_TYPE,
    _TYPE_ACTIVE_COLLAPSE_TOGGLE,
    TaskList,
)

_ALL = {t.value for t in TaskType}


@pytest.fixture
def repo(in_memory_db):
    run_migrations(in_memory_db)
    return TaskRepository(in_memory_db, db_path=":memory:")


def _make_task(
    repo: TaskRepository,
    *,
    tid: str,
    title: str,
    notes: str = "",
    status: Status = Status.PENDING,
    order_index: int = 1,
) -> Task:
    t = Task(
        id=tid,
        title=title,
        status=status,
        deps=[],
        notes=notes,
        order_index=order_index,
        created_at="2026-05-17T10:00:00",
    )
    repo.create(t)
    return t


def _add_sub(repo: TaskRepository, task_id: str, sub_type: TaskType, sid: str | None = None) -> None:
    repo.create_subtask(
        Subtask(
            id=sid or f"{task_id}-{sub_type.value}",
            task_id=task_id,
            text=f"{sub_type.value} sub",
            type=sub_type,
        )
    )


def _visible_task_ids(task_list: TaskList) -> list[str]:
    inner = task_list._inner
    return [
        inner.item(r).data(_ROLE_TASK_ID)
        for r in range(inner.count())
        if inner.item(r).data(_ROLE_TYPE) == "task"
    ]


def _visible_separators(task_list: TaskList) -> int:
    inner = task_list._inner
    return sum(
        1
        for r in range(inner.count())
        if inner.item(r).data(_ROLE_TYPE) == "separator"
    )


def _separator_widget_for(task_list: TaskList, sector: Sector):
    inner = task_list._inner
    for row in range(inner.count()):
        item = inner.item(row)
        if item.data(_ROLE_TYPE) == "separator" and item.data(_ROLE_SECTOR) == sector.value:
            return inner.itemWidget(item)
    return None


# ── Sem filtro (todos os tipos = filtro inativo) ────────────────────────────


def test_inner_list_uses_smooth_per_pixel_scroll(qtbot):
    from PySide6.QtWidgets import QAbstractItemView

    tl = TaskList()
    qtbot.addWidget(tl)
    inner = tl._inner
    # Rolagem suave por pixel (nao salta um card inteiro por entalhe da roda).
    assert inner.verticalScrollMode() == QAbstractItemView.ScrollMode.ScrollPerPixel
    assert inner.verticalScrollBar().singleStep() == 22


def test_no_filter_shows_all_four_sectors(qtbot, repo):
    _make_task(repo, tid="t1", title="alpha task")
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    assert _visible_separators(tl) == 4
    assert "t1" in _visible_task_ids(tl)


def test_active_and_waiting_sections_have_main_testids(qtbot, repo):
    _make_task(repo, tid="active", title="active", status=Status.IN_PROGRESS)
    _make_task(repo, tid="waiting", title="waiting", order_index=2)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    active = _separator_widget_for(tl, Sector.ACTIVE)
    waiting = _separator_widget_for(tl, Sector.WAITING)

    assert active is not None
    assert active.property("testid") == "task-list-active-section"
    assert waiting is not None
    assert waiting.property("testid") == "task-list-waiting-section"


# ── Regra dos 3 checkboxes: filtro inativo renderiza TODOS os cards ─────────


def test_all_types_selected_shows_card_even_without_subtasks(qtbot, repo):
    _make_task(repo, tid="t1", title="sem subtasks")
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    # Com os 3 tipos marcados o filtro e inativo: o card aparece mesmo sem subtasks.
    tl.set_filters(task_types=_ALL)
    assert _visible_task_ids(tl) == ["t1"]


def test_partial_filter_hides_card_without_subtasks(qtbot, repo):
    _make_task(repo, tid="t1", title="sem subtasks")
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    # Desmarcou tipos: a regra "renderiza mesmo sem subtasks" para de valer.
    tl.set_filters(task_types={"agent"})
    assert _visible_task_ids(tl) == []


# ── Filtro ativo: card visivel sse tem subtask do tipo selecionado ──────────


def test_filter_shows_only_cards_with_matching_subtasks(qtbot, repo):
    _make_task(repo, tid="t1", title="human card")
    _add_sub(repo, "t1", TaskType.HUMAN)
    _make_task(repo, tid="t2", title="dev card", order_index=2)
    _add_sub(repo, "t2", TaskType.DEV)
    _make_task(repo, tid="t3", title="agent card", order_index=3)
    _add_sub(repo, "t3", TaskType.AGENT)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.set_filters(task_types={"dev", "agent"})
    assert _visible_task_ids(tl) == ["t2", "t3"]


def test_only_agent_shows_only_cards_with_agent_subtasks(qtbot, repo):
    _make_task(repo, tid="t1", title="has agent")
    _add_sub(repo, "t1", TaskType.AGENT)
    _make_task(repo, tid="t2", title="only dev", order_index=2)
    _add_sub(repo, "t2", TaskType.DEV)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.set_filters(task_types={"agent"})
    assert _visible_task_ids(tl) == ["t1"]


def test_card_with_mixed_subtasks_matches_any_selected_type(qtbot, repo):
    _make_task(repo, tid="t1", title="mixed")
    _add_sub(repo, "t1", TaskType.AGENT, sid="t1-a")
    _add_sub(repo, "t1", TaskType.DEV, sid="t1-d")
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.set_filters(task_types={"dev"})
    assert _visible_task_ids(tl) == ["t1"]
    tl.set_filters(task_types={"human"})
    assert _visible_task_ids(tl) == []


def test_active_filter_hides_empty_sectors(qtbot, repo):
    # So existe uma task ACTIVE (in_progress) com subtask human; os demais
    # setores devem sumir sob filtro ativo.
    _make_task(repo, tid="t1", title="match me", status=Status.IN_PROGRESS)
    _add_sub(repo, "t1", TaskType.HUMAN)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.set_filters(task_types={"human"})

    assert _visible_separators(tl) == 1
    assert _visible_task_ids(tl) == ["t1"]


def test_clearing_filter_restores_all_sectors(qtbot, repo):
    _make_task(repo, tid="t1", title="alpha task")
    _add_sub(repo, "t1", TaskType.AGENT)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    # Nenhum tipo marcado -> nada casa.
    tl.set_filters(task_types=set())
    assert _visible_task_ids(tl) == []

    # Todos os tipos -> filtro inativo -> 4 setores e o card visivel.
    tl.set_filters(task_types=_ALL)
    assert _visible_separators(tl) == 4
    assert _visible_task_ids(tl) == ["t1"]


def test_visible_task_ids_helper(qtbot, repo):
    _make_task(repo, tid="t1", title="alpha task")
    _add_sub(repo, "t1", TaskType.HUMAN)
    _make_task(repo, tid="t2", title="other", order_index=2)
    _add_sub(repo, "t2", TaskType.DEV)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.set_filters(task_types={"human"})
    assert tl.visible_task_ids() == ["t1"]


def test_filter_persists_across_refresh(qtbot, repo):
    _make_task(repo, tid="t1", title="human")
    _add_sub(repo, "t1", TaskType.HUMAN)
    _make_task(repo, tid="t2", title="dev", order_index=2)
    _add_sub(repo, "t2", TaskType.DEV)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.set_filters(task_types={"human"})
    assert _visible_task_ids(tl) == ["t1"]

    # simula refresh de CRUD (sem args de filtro)
    tl.refresh(repo.list_active())
    assert _visible_task_ids(tl) == ["t1"]


def test_zero_matches_shows_empty_filter_label(qtbot, repo):
    _make_task(repo, tid="t1", title="refactor ui")
    _add_sub(repo, "t1", TaskType.AGENT)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.set_filters(task_types={"human"})

    assert not tl._empty_filter_label.isHidden()
    assert tl._empty_label.isHidden()
    assert _visible_task_ids(tl) == []


def test_apply_filter_alias(qtbot, repo):
    _make_task(repo, tid="t1", title="human")
    _add_sub(repo, "t1", TaskType.HUMAN)
    _make_task(repo, tid="t2", title="dev", order_index=2)
    _add_sub(repo, "t2", TaskType.DEV)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.apply_filter(task_types={"human"})
    assert _visible_task_ids(tl) == ["t1"]


def test_active_chevron_collapses_and_restores_lower_sectors(qtbot, repo):
    _make_task(repo, tid="active", title="active", status=Status.IN_PROGRESS)
    _make_task(repo, tid="waiting", title="waiting", status=Status.PENDING, order_index=2)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    toggle_row = next(
        r
        for r in range(tl._inner.count())
        if tl._inner.item(r).data(_ROLE_TYPE) == _TYPE_ACTIVE_COLLAPSE_TOGGLE
    )
    assert tl._inner.item(toggle_row).data(_ROLE_SECTOR) == 1
    assert tl._inner.item(toggle_row - 1).data(_ROLE_TYPE) == "task"
    assert tl._inner.item(toggle_row - 1).data(_ROLE_TASK_ID) == "active"
    assert tl._inner.item(toggle_row + 1).data(_ROLE_TYPE) == "separator"

    button = tl._inner.itemWidget(tl._inner.item(toggle_row)).findChild(
        QToolButton, "activeCollapseButton"
    )
    assert button is not None
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)

    assert _visible_task_ids(tl) == ["active"]
    assert _visible_separators(tl) == 1

    tl.refresh(repo.list_active())
    assert _visible_task_ids(tl) == ["active"]

    toggle_row = next(
        r
        for r in range(tl._inner.count())
        if tl._inner.item(r).data(_ROLE_TYPE) == _TYPE_ACTIVE_COLLAPSE_TOGGLE
    )
    button = tl._inner.itemWidget(tl._inner.item(toggle_row)).findChild(
        QToolButton, "activeCollapseButton"
    )
    assert button is not None
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)

    assert "waiting" in _visible_task_ids(tl)
    assert _visible_separators(tl) == 4
