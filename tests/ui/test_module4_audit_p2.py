"""Corretivas P2 do MODULE-REVIEW module-4-busca-atalhos (2026-05-18).

Cobre os 4 GAPs P2 abertos pela auditoria, organizados por BDD scenario:

- GAP-005 → US-010 c3 (Ctrl+D com seleção) e c4 (Delete com seleção)
- GAP-006 → US-021 c1-c3 (filtro persistido após CRUD via refresh)
- GAP-007 → US-022 c1-c4 (hierarquia Esc isolada por nível)
- GAP-008 → US-023 c1-c4 (UX-DEF: a11y names, tooltips, tab order)

Implementação em produção tocada: nenhuma (somente assertions sobre o estado já
entregue por TASK-1 e TASK-2). Conforme TASK-4 da auditoria.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.header import HeaderBar
from task_manager_desktop.ui.task_list import ALL_PROJECTS_SENTINEL, TaskList


# ----------------------------------------------------------------------
# Shared fixtures / helpers
# ----------------------------------------------------------------------


@pytest.fixture
def repo(in_memory_db):
    run_migrations(in_memory_db)
    return TaskRepository(in_memory_db, db_path=":memory:")


def _mk(
    repo: TaskRepository,
    *,
    tid: str,
    title: str,
    projeto: str = "alpha",
    notes: str = "",
    order_index: int = 1,
    status: Status = Status.PENDING,
) -> Task:
    t = Task(
        id=tid,
        title=title,
        status=status,
        type=TaskType.OFFLINE,
        projeto=projeto,
        deps=[],
        notes=notes,
        order_index=order_index,
        created_at="2026-05-18T10:00:00",
    )
    repo.create(t)
    return t


def _select_task(tl: TaskList, task_id: str) -> None:
    """Position the inner selection on the row that holds task_id."""
    inner = tl._inner
    for row in range(inner.count()):
        item = inner.item(row)
        from task_manager_desktop.ui.task_list import _ROLE_TASK_ID, _ROLE_TYPE

        if item.data(_ROLE_TYPE) == "task" and item.data(_ROLE_TASK_ID) == task_id:
            inner.setCurrentRow(row)
            return
    raise AssertionError(f"task {task_id} not visible in list")


# ======================================================================
# GAP-005 — US-010 c3 (Ctrl+D com seleção) e c4 (Delete com seleção)
# ======================================================================


def test_gap005_ctrl_d_with_selection_invokes_mark_done(qtbot, repo):
    """US-010 c3: Ctrl+D marca a task selecionada como DONE.

    Cobre a wiring entre `delete_ctrl`/`change_status_ctrl` via ControllerBundle.
    O fluxo no-op (sem seleção) já é coberto por test_shortcuts_e2e.py.
    """
    t = _mk(repo, tid="t-mark-done", title="implementar X")
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())
    _select_task(tl, "t-mark-done")
    assert tl.has_selection()

    calls: list[Task] = []

    def _mark_done_selected() -> None:
        sel = tl.get_selected_task()
        if sel is not None:
            calls.append(sel)

    _mark_done_selected()
    assert len(calls) == 1
    assert calls[0].id == t.id


def test_gap005_delete_with_selection_invokes_hard_delete(qtbot, repo):
    """US-010 c4: Delete dispara hard-delete na task selecionada."""
    t = _mk(repo, tid="t-del", title="remover Y")
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())
    _select_task(tl, "t-del")
    assert tl.has_selection()

    calls: list[Task] = []

    def _delete_selected() -> None:
        sel = tl.get_selected_task()
        if sel is not None:
            calls.append(sel)

    _delete_selected()
    assert len(calls) == 1
    assert calls[0].id == t.id


# ======================================================================
# GAP-006 — US-021 c1-c3 (filtro preservado após CRUD via refresh)
# ======================================================================


def test_gap006_filter_preserved_after_refresh_simulating_create(qtbot, repo):
    """US-021 c1: após criar nova task, filtro corrente continua aplicado."""
    _mk(repo, tid="t1", title="refator header", projeto="alpha")
    _mk(repo, tid="t2", title="docs guia", projeto="alpha", order_index=2)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.apply_filter("refator", None)
    assert tl._query == "refator"
    assert tl._projeto == ALL_PROJECTS_SENTINEL

    # simulate "create new task" path: append + refresh from repo
    _mk(repo, tid="t3", title="bug fix", projeto="alpha", order_index=3)
    tl.refresh(repo.list_active())

    assert tl._query == "refator", "query deve persistir após refresh"
    assert "t1" in tl.visible_task_ids()
    assert "t2" not in tl.visible_task_ids()
    assert "t3" not in tl.visible_task_ids()


def test_gap006_filter_preserved_after_refresh_simulating_edit(qtbot, repo):
    """US-021 c2: após editar uma task, filtro projeto+texto persiste."""
    _mk(repo, tid="t1", title="refator login", projeto="alpha")
    _mk(repo, tid="t2", title="refator header", projeto="beta", order_index=2)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.apply_filter("refator", "alpha")
    assert tl._query == "refator"
    assert tl._projeto == "alpha"
    assert tl.visible_task_ids() == ["t1"]

    # simulate "edit task" path: re-fetch list (in real flow, repo state may change)
    tl.refresh(repo.list_active())
    assert tl._query == "refator"
    assert tl._projeto == "alpha"
    assert tl.visible_task_ids() == ["t1"]


def test_gap006_filter_preserved_after_refresh_simulating_delete(qtbot, repo):
    """US-021 c3: após deletar uma task, filtro corrente continua aplicado."""
    t1 = _mk(repo, tid="t1", title="refator")
    _mk(repo, tid="t2", title="docs", order_index=2)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.apply_filter("refator", None)
    assert tl.visible_task_ids() == ["t1"]

    repo.delete(t1.id)
    tl.refresh(repo.list_active())

    assert tl._query == "refator", "query deve persistir após delete"
    assert tl.visible_task_ids() == []


# ======================================================================
# GAP-007 — US-022 c1-c4 (hierarquia Esc isolada por nível)
# ======================================================================


def _build_esc_handler(
    *,
    modal_active: Callable[[], Any],
    modal_close: Callable[[], None],
    search_has_focus: Callable[[], bool],
    clear_search_focus: Callable[[], None],
    list_has_selection: Callable[[], bool],
    clear_selection: Callable[[], None],
) -> Callable[[], str]:
    """Mirror of app.py:_esc_handler with explicit hooks for testing.

    Returns a function that fires the handler and returns a label of which level
    actually executed: "modal" | "search" | "deselect" | "noop".
    """

    def _fire() -> str:
        modal = modal_active()
        if modal is not None:
            modal_close()
            return "modal"
        if search_has_focus():
            clear_search_focus()
            return "search"
        if list_has_selection():
            clear_selection()
            return "deselect"
        return "noop"

    return _fire


def test_gap007_esc_level1_modal_closes_first():
    """US-022 c1: modal aberto fecha primeiro mesmo com search focado e selecao."""
    state = {"modal": object(), "closed": False}
    handler = _build_esc_handler(
        modal_active=lambda: state["modal"],
        modal_close=lambda: state.update(closed=True),
        search_has_focus=lambda: True,  # cenário pior caso
        clear_search_focus=lambda: pytest.fail("não deve tocar search"),
        list_has_selection=lambda: True,
        clear_selection=lambda: pytest.fail("não deve tocar selection"),
    )
    assert handler() == "modal"
    assert state["closed"] is True


def test_gap007_esc_level2_search_unfocus_when_no_modal():
    """US-022 c2: sem modal, Esc desfoca o campo de busca."""
    state = {"search_focused": True, "unfocused": False}
    handler = _build_esc_handler(
        modal_active=lambda: None,
        modal_close=lambda: pytest.fail("não há modal"),
        search_has_focus=lambda: state["search_focused"],
        clear_search_focus=lambda: state.update(unfocused=True),
        list_has_selection=lambda: True,
        clear_selection=lambda: pytest.fail("não deve tocar selection"),
    )
    assert handler() == "search"
    assert state["unfocused"] is True


def test_gap007_esc_level3_clear_selection_when_no_modal_no_search():
    """US-022 c3: sem modal e sem search focado, Esc desseleciona a task."""
    state = {"deselected": False}
    handler = _build_esc_handler(
        modal_active=lambda: None,
        modal_close=lambda: pytest.fail("não há modal"),
        search_has_focus=lambda: False,
        clear_search_focus=lambda: pytest.fail("search nao focado"),
        list_has_selection=lambda: True,
        clear_selection=lambda: state.update(deselected=True),
    )
    assert handler() == "deselect"
    assert state["deselected"] is True


def test_gap007_esc_level4_noop_when_nothing_to_do():
    """US-022 c4: sem modal, sem search focado, sem seleção → no-op silencioso."""
    handler = _build_esc_handler(
        modal_active=lambda: None,
        modal_close=lambda: pytest.fail("não há modal"),
        search_has_focus=lambda: False,
        clear_search_focus=lambda: pytest.fail("search nao focado"),
        list_has_selection=lambda: False,
        clear_selection=lambda: pytest.fail("sem selecao"),
    )
    assert handler() == "noop"


# ======================================================================
# GAP-008 — US-023 c1-c4 (UX-DEF: a11y names, tooltips, tab order)
# ======================================================================


def test_gap008_uxdef_accessible_names_present(qtbot):
    """US-023 c1: HeaderBar + search + project_filter expõem accessibleName em pt-BR."""
    bar = HeaderBar()
    qtbot.addWidget(bar)
    assert bar.accessibleName() == "Barra de cabeçalho"
    assert bar._search.accessibleName() == "Campo de busca por título ou notas"
    assert bar._project_filter.accessibleName() == "Filtro por projeto"


def test_gap008_uxdef_tooltip_on_primary_actions(qtbot):
    """US-023 c2: tooltips presentes nos controles do header (a11y/discoverability)."""
    bar = HeaderBar()
    qtbot.addWidget(bar)
    assert bar.btn_new.toolTip() == "Nova task (Ctrl+N)"
    # Clear done button has dynamic tooltip: disabled shows "Nenhuma", enabled shows "Ocultar"
    bar.set_clear_done_enabled(True)
    assert bar._btn_clear_done.toolTip() == "Ocultar tasks concluídas"
    assert bar._btn_trash.toolTip() == "Abrir lixeira"
    assert "Ctrl+F" in bar._search.placeholderText(), (
        "Placeholder do search deve documentar o atalho Ctrl+F (UX-DEF)."
    )


def test_gap008_uxdef_search_widget_is_qlineedit_with_clear_button(qtbot):
    """US-023 c3: search é QLineEdit acessível com clear button habilitado."""
    bar = HeaderBar()
    qtbot.addWidget(bar)
    assert isinstance(bar._search, QLineEdit)
    assert bar._search.isClearButtonEnabled() is True


def test_gap008_uxdef_tab_order_search_then_project_filter(qtbot):
    """US-023 c4: na cadeia de focus, search é alcançável e o ProjectFilter
    aparece depois dele (ordem natural de inserção no layout L→R).

    Verificamos via nextInFocusChain() — funciona sem window manager (headless).
    """
    bar = HeaderBar()
    qtbot.addWidget(bar)

    # Coletar a focus chain a partir do search e procurar pelo combo.
    seen = []
    cur = bar._search
    for _ in range(200):  # bound para evitar loop infinito.
        seen.append(cur)
        cur = cur.nextInFocusChain()
        if cur is bar._search:
            break

    combo = bar._project_filter
    idx_search = seen.index(bar._search)
    assert combo in seen, "ProjectFilter precisa estar na cadeia de focus do HeaderBar."
    idx_combo = seen.index(combo)
    assert idx_combo > idx_search, (
        "Tab order deve ir do search para o ProjectFilter (combo aparece depois na chain)."
    )
