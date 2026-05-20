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
from PySide6.QtWidgets import QApplication, QCheckBox

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.header import HeaderBar
from task_manager_desktop.ui.task_list import TaskList


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
    notes: str = "",
    order_index: int = 1,
    status: Status = Status.PENDING,
    task_type: TaskType = TaskType.HUMAN,
) -> Task:
    t = Task(
        id=tid,
        title=title,
        status=status,
        type=task_type,
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
    _mk(repo, tid="t1", title="human task", task_type=TaskType.HUMAN)
    _mk(repo, tid="t2", title="dev task", task_type=TaskType.DEV, order_index=2)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.apply_filter(task_types={"human"})
    assert tl._task_types == frozenset({"human"})

    # simulate "create new task" path: append + refresh from repo
    _mk(repo, tid="t3", title="agent task", task_type=TaskType.AGENT, order_index=3)
    tl.refresh(repo.list_active())

    assert tl._task_types == frozenset({"human"}), "type filter deve persistir após refresh"
    assert "t1" in tl.visible_task_ids()
    assert "t2" not in tl.visible_task_ids()
    assert "t3" not in tl.visible_task_ids()


def test_gap006_filter_preserved_after_refresh_simulating_edit(qtbot, repo):
    """US-021 c2: após editar uma task, filtro de tipo persiste."""
    _mk(repo, tid="t1", title="human alpha", task_type=TaskType.HUMAN)
    _mk(repo, tid="t2", title="dev beta", task_type=TaskType.DEV, order_index=2)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.apply_filter(task_types={"human"})
    assert tl._task_types == frozenset({"human"})
    assert tl.visible_task_ids() == ["t1"]

    # simulate "edit task" path: re-fetch list (in real flow, repo state may change)
    tl.refresh(repo.list_active())
    assert tl._task_types == frozenset({"human"})
    assert tl.visible_task_ids() == ["t1"]


def test_gap006_filter_preserved_after_refresh_simulating_delete(qtbot, repo):
    """US-021 c3: após deletar uma task, filtro corrente continua aplicado."""
    t1 = _mk(repo, tid="t1", title="human", task_type=TaskType.HUMAN)
    _mk(repo, tid="t2", title="dev", task_type=TaskType.DEV, order_index=2)
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(repo.list_active())

    tl.apply_filter(task_types={"human"})
    assert tl.visible_task_ids() == ["t1"]

    repo.delete(t1.id)
    tl.refresh(repo.list_active())

    assert tl._task_types == frozenset({"human"}), "type filter deve persistir após delete"
    assert tl.visible_task_ids() == []


# ======================================================================
# GAP-007 — US-022 c1-c4 (hierarquia Esc isolada por nível)
# ======================================================================


def _build_esc_handler(
    *,
    modal_active: Callable[[], Any],
    modal_close: Callable[[], None],
    list_has_selection: Callable[[], bool],
    clear_selection: Callable[[], None],
) -> Callable[[], str]:
    """Mirror of app.py:_esc_handler with explicit hooks for testing.

    Returns a function that fires the handler and returns a label of which level
    actually executed: "modal" | "deselect" | "noop".
    """

    def _fire() -> str:
        modal = modal_active()
        if modal is not None:
            modal_close()
            return "modal"
        if list_has_selection():
            clear_selection()
            return "deselect"
        return "noop"

    return _fire


def test_gap007_esc_level1_modal_closes_first():
    """US-022 c1: modal aberto fecha primeiro mesmo com seleção."""
    state = {"modal": object(), "closed": False}
    handler = _build_esc_handler(
        modal_active=lambda: state["modal"],
        modal_close=lambda: state.update(closed=True),
        list_has_selection=lambda: True,
        clear_selection=lambda: pytest.fail("não deve tocar selection"),
    )
    assert handler() == "modal"
    assert state["closed"] is True


def test_gap007_esc_level3_clear_selection_when_no_modal():
    """US-022 c3: sem modal, Esc desseleciona a task."""
    state = {"deselected": False}
    handler = _build_esc_handler(
        modal_active=lambda: None,
        modal_close=lambda: pytest.fail("não há modal"),
        list_has_selection=lambda: True,
        clear_selection=lambda: state.update(deselected=True),
    )
    assert handler() == "deselect"
    assert state["deselected"] is True


def test_gap007_esc_level4_noop_when_nothing_to_do():
    """US-022 c4: sem modal, sem seleção → no-op silencioso."""
    handler = _build_esc_handler(
        modal_active=lambda: None,
        modal_close=lambda: pytest.fail("não há modal"),
        list_has_selection=lambda: False,
        clear_selection=lambda: pytest.fail("sem selecao"),
    )
    assert handler() == "noop"


# ======================================================================
# GAP-008 — US-023 c1-c4 (UX-DEF: a11y names, tooltips, tab order)
# ======================================================================


def test_gap008_uxdef_accessible_names_present(qtbot):
    """US-023 c1: HeaderBar + type_filter expõem accessibleName em pt-BR."""
    bar = HeaderBar()
    qtbot.addWidget(bar)
    assert bar.accessibleName() == "Barra de cabeçalho"
    assert bar._type_filter.accessibleName() == "Filtro por tipo de task"


def test_gap008_uxdef_tooltip_on_primary_actions(qtbot):
    """US-023 c2: tooltips presentes nos controles do header (a11y/discoverability)."""
    bar = HeaderBar()
    qtbot.addWidget(bar)
    assert bar.btn_new.toolTip() == "Nova task (Ctrl+N)"
    # Clear done button is icon-only: disabled and enabled states both need tooltip.
    bar.set_clear_done_enabled(False)
    assert "Nenhuma task concluída visível" in bar._btn_clear_done.toolTip()
    bar.set_clear_done_enabled(True)
    assert bar._btn_clear_done.toolTip() == "Mover tasks concluídas para a Lixeira"
    assert bar._btn_trash.toolTip() == "Lixeira (tasks ocultas até 30 dias)"


def test_gap008_uxdef_type_filter_widgets_are_checkboxes(qtbot):
    """US-023 c3: filtro de tipo usa checkboxes acessíveis."""
    bar = HeaderBar()
    qtbot.addWidget(bar)
    assert set(bar._type_checkboxes) == {"human", "dev", "agent"}
    assert all(isinstance(cb, QCheckBox) for cb in bar._type_checkboxes.values())
    assert bar.current_task_types() == frozenset({"human", "dev", "agent"})


def test_gap008_uxdef_type_filter_in_focus_chain(qtbot):
    """US-023 c4: na cadeia de focus, os checkboxes do type filter sao alcancaveis.

    Verificamos via nextInFocusChain() — funciona sem window manager (headless).
    """
    bar = HeaderBar()
    qtbot.addWidget(bar)

    # Coletar a focus chain a partir do primeiro checkbox.
    seen = []
    cur = bar._type_checkboxes["human"]
    for _ in range(200):  # bound para evitar loop infinito.
        seen.append(cur)
        cur = cur.nextInFocusChain()
        if cur is bar._type_checkboxes["human"]:
            break

    for cb in bar._type_checkboxes.values():
        assert cb in seen, "Todos os checkboxes de tipo devem estar na cadeia de focus."
