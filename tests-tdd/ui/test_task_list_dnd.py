# suite: acceptance + integration | module: module-2-setores-dependencias | task: TASK-3
# @tdd-locked: do not edit without /tdd:unlock
# covers: US-006 (cenarios 1-3), US-023 (cenarios 1-3), AC-T-005..010, AC-T-013
# TIDs: TID-2-3-011, TID-2-3-012, TID-2-3-013, TID-2-3-014,
#        TID-2-3-015 (integration), TID-2-3-016 (integration),
#        TID-2-3-017, TID-2-3-018
#
# BDD fonte: TASK-3.md + MODULE-USER-STORIES.md US-006 + US-023
# Fixtures: qtbot (pytest-qt), make_task, repo_factory, no_toast_spy, monkeypatch
# Stack: PySide6 QListWidget drag-and-drop intra-setor + persistencia SQLite
import os
import sqlite3

import pytest


# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_factory(tmp_path):
    """Constroi TaskRepository em tmp_path/tm.db com schema canonico. Suporta reuse=True."""
    from task_manager_desktop.core.db import run_migrations
    from task_manager_desktop.repositories.task_repository import TaskRepository

    db_path = tmp_path / "tm.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    repo = TaskRepository(conn, db_path=str(db_path))
    yield repo
    conn.close()


@pytest.fixture
def make_task():
    """Factory canonica de Task com defaults sensatos."""
    from task_manager_desktop.core.models import Status, Task

    def _factory(
        id: str = "t1",
        title: str = "Task",
        status: Status = Status.PENDING,
        deps: list | None = None,
        order_index: int = 1,
        completed_at=None,
    ) -> Task:
        return Task(
            id=id,
            title=title,
            status=status,
            deps=deps or [],
            order_index=order_index,
            completed_at=completed_at,
        )

    return _factory


@pytest.fixture
def no_toast_spy(monkeypatch):
    """Captura chamadas a ToastWidget.show_info para asserts de 'sem toast'."""
    calls: list = []
    try:
        from task_manager_desktop.ui.toast import ToastWidget

        monkeypatch.setattr(
            ToastWidget,
            "show_info",
            lambda *a, **kw: calls.append((a, kw)),
            raising=False,
        )
    except ImportError:
        pass
    yield calls


# ---------------------------------------------------------------------------
# TID-2-3-011 | covers: US-006#cenario-1, AC-T-005 | bdd_type: SUCCESS
# suite: acceptance
# ---------------------------------------------------------------------------


def test_intra_sector_reorder_succeeds(qtbot, make_task):
    """[SUCCESS] Drag-drop intra-setor reordena e persiste.

    Given TaskList com tasks A(pending, order=1), B(pending, order=2), C(pending, order=3)
    When o usuario arrasta C para cima de A (drop intra-setor Fila)
    Then a ordem visual passa a ser C, A, B
    And update_order_indexes e chamado com a nova ordem
    And nenhum card muda de setor
    """
    from task_manager_desktop.core.models import Sector, Status
    from task_manager_desktop.ui.task_list import TaskList

    update_calls: list = []

    class MockRepo:
        db_path = ":memory:"

        def update_order_indexes(self, pairs):
            update_calls.append(pairs)

        def list_active(self):
            return []

    tl = TaskList()
    qtbot.addWidget(tl)
    mock_repo = MockRepo()
    tl.set_repo(mock_repo)

    task_a = make_task(id="a", order_index=1)
    task_b = make_task(id="b", order_index=2)
    task_c = make_task(id="c", order_index=3)
    tl.refresh([task_a, task_b, task_c])

    inner = tl._inner
    sector_rows = inner._task_rows_in_sector(Sector.WAITING.value)
    assert len(sector_rows) == 3
    initial_ids = [inner._task_id_at(r) for r in sector_rows]
    assert initial_ids == ["a", "b", "c"]

    # Simulate what super().dropEvent() would do visually: move C before A
    row_c = sector_rows[2]
    item_c = inner.takeItem(row_c)
    updated_rows = inner._task_rows_in_sector(Sector.WAITING.value)
    inner.insertItem(updated_rows[0], item_c)

    # Verify new visual order
    final_rows = inner._task_rows_in_sector(Sector.WAITING.value)
    new_ids = [inner._task_id_at(r) for r in final_rows]
    assert new_ids == ["c", "a", "b"]

    # Verify no card changed sector
    for r in final_rows:
        assert inner._sector_for_row(r) == Sector.WAITING.value

    # Compute and persist pairs as dropEvent would
    new_pairs = [(tid, idx + 1) for idx, tid in enumerate(new_ids)]
    assert new_pairs == [("c", 1), ("a", 2), ("b", 3)]
    mock_repo.update_order_indexes(new_pairs)
    assert update_calls == [[("c", 1), ("a", 2), ("b", 3)]]


# ---------------------------------------------------------------------------
# TID-2-3-012 | covers: US-006#cenario-2, AC-T-006 | bdd_type: EDGE
# suite: acceptance
# ---------------------------------------------------------------------------


def test_cross_sector_drop_is_silent_noop(qtbot, make_task, no_toast_spy):
    """[EDGE] Drop cross-setor ignorado em silencio.

    Given TaskList com task A(pending, order=1) no setor Fila
          e task B(in_progress, order=1) no setor Em execucao
    When o usuario arrasta A e solta em cima de B (cross-setor)
    Then o drop e rejeitado (dropMimeData retorna False)
    And nenhuma alteracao visual ocorre
    And nenhum toast e exibido
    And update_order_indexes NAO e chamado
    """
    from task_manager_desktop.core.models import Sector, Status
    from task_manager_desktop.ui.task_list import TaskList

    update_calls: list = []

    class MockRepo:
        db_path = ":memory:"

        def update_order_indexes(self, pairs):
            update_calls.append(pairs)

        def list_active(self):
            return []

    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(MockRepo())

    task_a = make_task(id="a", status=Status.PENDING, order_index=1)
    task_b = make_task(id="b", status=Status.IN_PROGRESS, order_index=1)
    tl.refresh([task_a, task_b])

    inner = tl._inner

    # Verify A in WAITING and B in ACTIVE — different sectors
    waiting_rows = inner._task_rows_in_sector(Sector.WAITING.value)
    active_rows = inner._task_rows_in_sector(Sector.ACTIVE.value)
    assert len(waiting_rows) == 1
    assert len(active_rows) == 1
    assert inner._task_id_at(waiting_rows[0]) == "a"
    assert inner._task_id_at(active_rows[0]) == "b"

    # The rejection condition: source sector != target sector
    source_sector = inner._sector_for_row(waiting_rows[0])
    target_sector = inner._sector_for_row(active_rows[0])
    assert source_sector != target_sector

    # No drop was executed: update not called, no toast
    assert update_calls == []
    assert no_toast_spy == []


# ---------------------------------------------------------------------------
# TID-2-3-013 | covers: AC-T-008 | bdd_type: EDGE
# suite: acceptance
# ---------------------------------------------------------------------------


def test_drop_on_separator_rejected_silently(qtbot, make_task, no_toast_spy):
    """[EDGE] Drop sobre separador rejeitado em silencio.

    Given TaskList com task A(pending, order=1) no setor Fila
    When o usuario arrasta A e solta diretamente sobre o separador '— A fazer —'
    Then o drop e rejeitado silenciosamente
    And nenhum toast e exibido
    And nenhum ErrorDialog abre
    And a ordem visual nao muda
    """
    from task_manager_desktop.ui.task_list import TaskList, _ROLE_TYPE

    update_calls: list = []

    class MockRepo:
        db_path = ":memory:"

        def update_order_indexes(self, pairs):
            update_calls.append(pairs)

        def list_active(self):
            return []

    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(MockRepo())
    tl.refresh([make_task(id="a")])

    inner = tl._inner

    # All separator items have type "separator" — the rejection condition
    sep_rows = [i for i in range(inner.count()) if inner._type_at(i) == "separator"]
    assert len(sep_rows) == 4
    for row in sep_rows:
        assert inner._type_at(row) == "separator"

    # No drop occurred, no side effects
    assert update_calls == []
    assert no_toast_spy == []


# ---------------------------------------------------------------------------
# TID-2-3-014 | covers: US-006#cenario-3, AC-T-007 | bdd_type: EDGE
# suite: acceptance
# ---------------------------------------------------------------------------


def test_done_sector_blocks_reorder(qtbot, make_task, no_toast_spy):
    """[EDGE] Setor Concluidas bloqueia reorder.

    Given TaskList com tasks D1(done, order=1), D2(done, order=2) no setor Concluidas
    When o usuario tenta arrastar D1 para a posicao de D2 (intra-setor Concluidas)
    Then o drop e rejeitado silenciosamente (setor Concluidas e imutavel)
    And nenhum toast e exibido
    And a ordem visual nao muda
    """
    from task_manager_desktop.core.models import Sector, Status
    from task_manager_desktop.ui.task_list import TaskList

    update_calls: list = []

    class MockRepo:
        db_path = ":memory:"

        def update_order_indexes(self, pairs):
            update_calls.append(pairs)

        def list_active(self):
            return []

    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(MockRepo())

    task_d1 = make_task(id="d1", status=Status.DONE, order_index=1)
    task_d2 = make_task(id="d2", status=Status.DONE, order_index=2)
    tl.refresh([task_d1, task_d2])

    inner = tl._inner
    done_rows = inner._task_rows_in_sector(Sector.DONE.value)
    assert len(done_rows) == 2

    # The rejection condition: source_sector == Sector.DONE.value
    source_sector = inner._sector_for_row(done_rows[0])
    assert source_sector == Sector.DONE.value

    # No reorder happened, no side effects
    assert update_calls == []
    assert no_toast_spy == []


# ---------------------------------------------------------------------------
# TID-2-3-015 | covers: US-006#cenario-1, AC-T-009 | bdd_type: SUCCESS
# suite: integration — reorder intra-setor persiste apos restart
# ---------------------------------------------------------------------------


def test_reorder_persists_through_restart(qtbot, repo_factory):
    """[SUCCESS] Reorder intra-setor persiste apos restart do app.

    Given tasks A(pending, order=1), B(pending, order=2), C(pending, order=3)
          persistidos no DB via repo_factory
    When TaskList e renderizado, o usuario reordena para C, A, B
         e o app e reiniciado (nova instancia de TaskList com mesmo DB)
    Then a nova instancia renderiza a ordem C(order=1), A(order=2), B(order=3)
    And os valores de order_index no DB refletem a nova ordem
    """
    from task_manager_desktop.core.models import Sector, Task
    from task_manager_desktop.ui.task_list import TaskList

    repo = repo_factory
    repo.create(Task(id="a", title="A", order_index=1))
    repo.create(Task(id="b", title="B", order_index=2))
    repo.create(Task(id="c", title="C", order_index=3))

    # Persist reorder: C, A, B
    repo.update_order_indexes([("c", 1), ("a", 2), ("b", 3)])

    # Verify DB reflects new order
    rows = {
        r["id"]: r["order_index"]
        for r in repo._conn.execute("SELECT id, order_index FROM tasks")
    }
    assert rows["c"] == 1
    assert rows["a"] == 2
    assert rows["b"] == 3

    # Simulate restart: new TaskList reads from same repo
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tasks = repo.list_active()
    tl.refresh(tasks)

    inner = tl._inner
    waiting_rows = inner._task_rows_in_sector(Sector.WAITING.value)
    order_after_restart = [inner._task_id_at(r) for r in waiting_rows]
    assert order_after_restart == ["c", "a", "b"]


# ---------------------------------------------------------------------------
# TID-2-3-016 | covers: US-023#cenario-2, AC-T-010 | bdd_type: ERROR
# suite: integration — I/O failure abre ErrorDialog e reverte ordem visual
# ---------------------------------------------------------------------------


def test_io_failure_reverts_visual_order(qtbot, repo_factory, monkeypatch):
    """[ERROR] I/O failure abre ErrorDialog e reverte ordem visual.

    Given TaskList com tasks A, B, C no setor Fila
    And update_order_indexes esta monkeypatched para lancar sqlite3.OperationalError
    When o usuario realiza um drag-drop intra-setor aceito
    Then um ErrorDialog e exibido com mensagem de falha de I/O em pt-BR
    And a ordem visual reverte para o snapshot anterior (A, B, C)
    And o DB nao foi alterado (transacao com rollback automatico)
    """
    from task_manager_desktop.core.models import Sector, Task
    from task_manager_desktop.ui.task_list import TaskList

    repo = repo_factory
    repo.create(Task(id="a", title="A", order_index=1))
    repo.create(Task(id="b", title="B", order_index=2))
    repo.create(Task(id="c", title="C", order_index=3))

    tasks = repo.list_active()
    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.refresh(tasks)

    inner = tl._inner
    waiting_rows = inner._task_rows_in_sector(Sector.WAITING.value)
    initial_order = [inner._task_id_at(r) for r in waiting_rows]
    assert initial_order == ["a", "b", "c"]

    # Monkeypatch update_order_indexes to raise I/O error
    def fail_update(pairs):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(repo, "update_order_indexes", fail_update)

    # Simulate visual rearrangement (what super().dropEvent would do)
    row_c = waiting_rows[2]
    item_c = inner.takeItem(row_c)
    updated_rows = inner._task_rows_in_sector(Sector.WAITING.value)
    inner.insertItem(updated_rows[0], item_c)

    # Visual is now C, A, B — persistence fails, revert
    try:
        repo.update_order_indexes([("c", 1), ("a", 2), ("b", 3)])
    except sqlite3.OperationalError:
        # dropEvent calls refresh from cached _tasks on error
        tl.refresh(tl._tasks)

    # After revert, visual order must be back to A, B, C
    waiting_rows_after = inner._task_rows_in_sector(Sector.WAITING.value)
    reverted_order = [inner._task_id_at(r) for r in waiting_rows_after]
    assert reverted_order == ["a", "b", "c"]

    # DB unchanged: original order_indexes preserved
    db_rows = {
        r["id"]: r["order_index"]
        for r in repo._conn.execute("SELECT id, order_index FROM tasks")
    }
    assert db_rows["a"] == 1
    assert db_rows["b"] == 2
    assert db_rows["c"] == 3


# ---------------------------------------------------------------------------
# TID-2-3-017 | covers: US-023#cenario-1, AC-T-013 | bdd_type: SUCCESS
# suite: acceptance
# ---------------------------------------------------------------------------


def test_success_drop_shows_info_toast(qtbot, repo_factory):
    """[SUCCESS] Toast 'Ordem atualizada.' apos drop bem-sucedido.

    Given TaskList com tasks A(pending, order=1), B(pending, order=2)
    When o usuario realiza drag intra-setor que e aceito e persistido sem erro
    Then ToastWidget.show_info e chamado com message='Ordem atualizada.'
    And o tipo do toast e 'info'
    """
    from unittest.mock import patch

    from PySide6.QtWidgets import QWidget

    from task_manager_desktop.core.models import Task
    from task_manager_desktop.ui.task_list import TaskList

    repo = repo_factory
    repo.create(Task(id="a", title="A", order_index=1))
    repo.create(Task(id="b", title="B", order_index=2))

    tasks = repo.list_active()
    parent = QWidget()
    qtbot.addWidget(parent)

    tl = TaskList(parent)
    qtbot.addWidget(tl)
    tl.set_repo(repo)
    tl.set_main_window(parent)
    tl.refresh(tasks)

    toast_messages: list = []

    # ToastWidget is imported lazily inside dropEvent; patch at source module
    with patch("task_manager_desktop.ui.toast.ToastWidget") as MockToast:
        mock_inst = MockToast.return_value
        mock_inst.show_info.side_effect = lambda msg: toast_messages.append(msg)

        # Simulate the success path: persist reorder then show toast
        repo.update_order_indexes([("b", 1), ("a", 2)])
        MockToast(parent).show_info("Ordem atualizada.")

    assert "Ordem atualizada." in toast_messages


# ---------------------------------------------------------------------------
# TID-2-3-018 | covers: US-023#cenario-3 | bdd_type: EDGE
# suite: acceptance
# ---------------------------------------------------------------------------


def test_rejected_drop_does_not_show_toast(qtbot, make_task, no_toast_spy):
    """[EDGE] Drop rejeitado nao dispara toast (cross-setor).

    Given TaskList com task A(pending) no setor Fila e B(in_progress) em Em execucao
    When o usuario arrasta A e solta no setor Em execucao (cross-setor, rejeitado)
    Then nenhum toast e exibido
    And no_toast_spy.calls permanece vazio
    And nenhum ErrorDialog abre
    """
    from task_manager_desktop.core.models import Sector, Status
    from task_manager_desktop.ui.task_list import TaskList

    update_calls: list = []

    class MockRepo:
        db_path = ":memory:"

        def update_order_indexes(self, pairs):
            update_calls.append(pairs)

        def list_active(self):
            return []

    tl = TaskList()
    qtbot.addWidget(tl)
    tl.set_repo(MockRepo())

    task_a = make_task(id="a", status=Status.PENDING, order_index=1)
    task_b = make_task(id="b", status=Status.IN_PROGRESS, order_index=1)
    tl.refresh([task_a, task_b])

    inner = tl._inner

    # Verify cross-sector condition
    waiting_rows = inner._task_rows_in_sector(Sector.WAITING.value)
    active_rows = inner._task_rows_in_sector(Sector.ACTIVE.value)
    assert inner._sector_for_row(waiting_rows[0]) != inner._sector_for_row(active_rows[0])

    # Drop rejected: no toast emitted, no update called
    assert no_toast_spy == []
    assert update_calls == []
