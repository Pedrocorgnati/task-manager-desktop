# suite: acceptance | module: module-2-setores-dependencias | task: TASK-2
# @tdd-locked: do not edit without /tdd:unlock
# covers: US-005 (cenarios 1-4) — Promocao e rebaixamento automatico de dependentes diretos
# TIDs: TID-2-2-015, TID-2-2-016, TID-2-2-017, TID-2-2-018
#
# BDD fonte: TASK-2.md §BDD + MODULE-USER-STORIES.md US-005
# Fixtures: qtbot (pytest-qt), repo_factory, no_toast_spy
# Regra invariante: propagacao e de UM NIVEL APENAS (D-006)
import sqlite3

import pytest

# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_factory(tmp_path):
    """Constroi TaskRepository em tmp_path/tm.db com schema canonico."""
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
# TID-2-2-015 | covers: US-005#cenario-1 | bdd_type: SUCCESS
# ---------------------------------------------------------------------------


def test_us_005_cen_1_dependents_promoted_on_done(qtbot, repo_factory):
    """[SUCCESS] Two dependents promoted on dep done.

    Given tasks A (pending, no deps), B (pending, deps=[A]), C (pending, deps=[A])
    When A status changes to done
    Then B and C are recalculated to setor Fila (pending, no open deps)
    And B and C are NOT in setor Bloqueadas anymore
    And the propagation completes in one level only (not recursive)
    """
    from task_manager_desktop.controllers.change_status_controller import ChangeStatusController
    from task_manager_desktop.core.models import Sector, Task
    from task_manager_desktop.ui.task_list import _ROLE_SECTOR, _ROLE_TASK_ID, _ROLE_TYPE, TaskList

    repo = repo_factory
    task_a = Task(id="aaa", title="A", deps=[], order_index=1)
    task_b = Task(id="bbb", title="B", deps=["aaa"], order_index=2)
    task_c = Task(id="ccc", title="C", deps=["aaa"], order_index=3)
    repo.create(task_a)
    repo.create(task_b)
    repo.create(task_c)

    task_list = TaskList()
    task_list.set_repo(repo)
    task_list.refresh([task_a, task_b, task_c])
    qtbot.addWidget(task_list)

    class _NoopError:
        def show_io_error(self, *a, **kw):
            pass

    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: {t.id: t for t in repo.list_active()},
        error_handler=_NoopError(),
        refresh_card=lambda t: None,
        task_list=task_list,
    )

    ctrl.change_status(task_a, "done")

    # Verify B and C are in WAITING sector
    inner = task_list._inner
    sectors: dict[str, int] = {}
    for i in range(inner.count()):
        item = inner.item(i)
        if item and item.data(_ROLE_TYPE) == "task":
            sectors[item.data(_ROLE_TASK_ID)] = item.data(_ROLE_SECTOR)

    assert sectors.get("bbb") == Sector.WAITING, f"B deve estar em WAITING. sectors={sectors}"
    assert sectors.get("ccc") == Sector.WAITING, f"C deve estar em WAITING. sectors={sectors}"
    assert sectors.get("bbb") != Sector.BLOCKED
    assert sectors.get("ccc") != Sector.BLOCKED


# ---------------------------------------------------------------------------
# TID-2-2-016 | covers: US-005#cenario-2 | bdd_type: EDGE
# ---------------------------------------------------------------------------


def test_us_005_cen_2_dependent_with_other_open_dep_stays_blocked(qtbot, repo_factory):
    """[EDGE] Dependent with another open dep stays Bloqueadas.

    Given tasks A (pending, no deps), E (pending, no deps),
          D (pending, deps=[A, E])
    When A status changes to done
    Then D remains in setor Bloqueadas (has open dep E)
    And D is NOT promoted to Fila
    """
    from task_manager_desktop.controllers.change_status_controller import ChangeStatusController
    from task_manager_desktop.core.models import Sector, Task
    from task_manager_desktop.ui.task_list import _ROLE_SECTOR, _ROLE_TASK_ID, _ROLE_TYPE, TaskList

    repo = repo_factory
    task_a = Task(id="aaa", title="A", deps=[], order_index=1)
    task_e = Task(id="eee", title="E", deps=[], order_index=2)
    task_d = Task(id="ddd", title="D", deps=["aaa", "eee"], order_index=3)
    repo.create(task_a)
    repo.create(task_e)
    repo.create(task_d)

    task_list = TaskList()
    task_list.set_repo(repo)
    task_list.refresh([task_a, task_e, task_d])
    qtbot.addWidget(task_list)

    class _NoopError:
        def show_io_error(self, *a, **kw):
            pass

    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: {t.id: t for t in repo.list_active()},
        error_handler=_NoopError(),
        refresh_card=lambda t: None,
        task_list=task_list,
    )

    ctrl.change_status(task_a, "done")

    inner = task_list._inner
    sectors: dict[str, int] = {}
    for i in range(inner.count()):
        item = inner.item(i)
        if item and item.data(_ROLE_TYPE) == "task":
            sectors[item.data(_ROLE_TASK_ID)] = item.data(_ROLE_SECTOR)

    assert sectors.get("ddd") == Sector.BLOCKED, f"D deve permanecer BLOCKED. sectors={sectors}"
    assert sectors.get("ddd") != Sector.WAITING


# ---------------------------------------------------------------------------
# TID-2-2-017 | covers: US-005#cenario-3 | bdd_type: EDGE
# ---------------------------------------------------------------------------


def test_us_005_cen_3_revert_status_demotes_dependents(qtbot, repo_factory):
    """[EDGE] Reverting done re-blocks dependents.

    Given tasks A (done), B (pending, deps=[A]) currently in Fila
    When A status reverts to pending
    Then B is recalculated to setor Bloqueadas (has open dep A again)
    And B is removed from Fila
    """
    from datetime import datetime, timezone

    from task_manager_desktop.controllers.change_status_controller import ChangeStatusController
    from task_manager_desktop.core.models import Sector, Status, Task
    from task_manager_desktop.ui.task_list import _ROLE_SECTOR, _ROLE_TASK_ID, _ROLE_TYPE, TaskList

    repo = repo_factory
    task_a = Task(id="aaa", title="A", deps=[], order_index=1)
    task_b = Task(id="bbb", title="B", deps=["aaa"], order_index=2)
    repo.create(task_a)
    repo.create(task_b)

    # Set A as done in DB
    repo.update_status("aaa", Status.DONE, datetime.now(timezone.utc).replace(tzinfo=None))
    task_a.status = Status.DONE

    task_list = TaskList()
    task_list.set_repo(repo)
    task_list.refresh(repo.list_active())
    qtbot.addWidget(task_list)

    class _NoopError:
        def show_io_error(self, *a, **kw):
            pass

    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: {t.id: t for t in repo.list_active()},
        error_handler=_NoopError(),
        refresh_card=lambda t: None,
        task_list=task_list,
    )

    # Revert A from done to pending
    ctrl.change_status(task_a, "pending")

    inner = task_list._inner
    sectors: dict[str, int] = {}
    for i in range(inner.count()):
        item = inner.item(i)
        if item and item.data(_ROLE_TYPE) == "task":
            sectors[item.data(_ROLE_TASK_ID)] = item.data(_ROLE_SECTOR)

    assert sectors.get("bbb") == Sector.BLOCKED, f"B deve estar BLOCKED apos revert. sectors={sectors}"
    assert sectors.get("bbb") != Sector.WAITING


# ---------------------------------------------------------------------------
# TID-2-2-018 | covers: US-005#cenario-4, UX-2-2 | bdd_type: SUCCESS
# ---------------------------------------------------------------------------


def test_us_005_cen_4_chain_propagation_one_level_only(qtbot, repo_factory, no_toast_spy):
    """[SUCCESS] Chain propagation is one level only + silent (no extra toast).

    Given tasks C (pending, no deps), B (pending, deps=[C]), A (pending, deps=[B])
    When C status changes to done
    Then B is promoted to Fila (direct dependent of C — level 1)
    And A remains in Bloqueadas (dep B still pending — NOT propagated transitively)
    And no additional toast is emitted for B or A (propagacao silenciosa, UX-2-2)
    """
    from task_manager_desktop.controllers.change_status_controller import ChangeStatusController
    from task_manager_desktop.core.models import Sector, Task
    from task_manager_desktop.ui.task_list import _ROLE_SECTOR, _ROLE_TASK_ID, _ROLE_TYPE, TaskList

    repo = repo_factory
    # Chain: A depends on B, B depends on C
    task_c = Task(id="ccc", title="C", deps=[], order_index=1)
    task_b = Task(id="bbb", title="B", deps=["ccc"], order_index=2)
    task_a = Task(id="aaa", title="A", deps=["bbb"], order_index=3)
    repo.create(task_c)
    repo.create(task_b)
    repo.create(task_a)

    task_list = TaskList()
    task_list.set_repo(repo)
    task_list.refresh([task_c, task_b, task_a])
    qtbot.addWidget(task_list)

    class _NoopError:
        def show_io_error(self, *a, **kw):
            pass

    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: {t.id: t for t in repo.list_active()},
        error_handler=_NoopError(),
        refresh_card=lambda t: None,
        task_list=task_list,
    )

    ctrl.change_status(task_c, "done")

    inner = task_list._inner
    sectors: dict[str, int] = {}
    for i in range(inner.count()):
        item = inner.item(i)
        if item and item.data(_ROLE_TYPE) == "task":
            sectors[item.data(_ROLE_TASK_ID)] = item.data(_ROLE_SECTOR)

    # B is direct dep of C → promoted to WAITING
    assert sectors.get("bbb") == Sector.WAITING, f"B deve estar em WAITING. sectors={sectors}"
    # A depends on B (not C) → stays BLOCKED (B is still pending)
    assert sectors.get("aaa") == Sector.BLOCKED, f"A deve permanecer BLOCKED. sectors={sectors}"
