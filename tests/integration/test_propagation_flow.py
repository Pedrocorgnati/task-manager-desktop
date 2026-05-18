# suite: integration | module: module-2-setores-dependencias | task: TASK-2
# @tdd-unlocked: 2026-05-18 (TASK-4/ST006 — import movido para core.constants)
# covers: TASK-2/ST006, AC-T-006, AC-T-008 — propagacao end-to-end (controller + repo + task_list spy)
# target: task_manager_desktop/controllers/change_status_controller.py wire-up propagacao
# TIDs: TID-2-2-010, TID-2-2-011, TID-2-2-012, TID-2-2-013, TID-2-2-014
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
def mock_task_list():
    """Spy de TaskList.move_card_to_sector e refresh; captura argumentos por chamada."""

    class _MockTaskList:
        def __init__(self):
            self.moves: list[tuple[str, int]] = []
            self.refresh_calls: int = 0

        def move_card_to_sector(self, task_id: str, sector: int) -> None:
            self.moves.append((task_id, sector))

        def refresh(self) -> None:
            self.refresh_calls += 1

    return _MockTaskList()


# ---------------------------------------------------------------------------
# TID-2-2-010 | covers: TASK-2/ST006
# ---------------------------------------------------------------------------


def test_change_a_to_done_moves_b_c_to_fila(repo_factory, mock_task_list):
    """Integration: mudar A para done move B e C (dependentes diretos) para Fila.

    Given A(pending, no deps), B(pending, deps=[A]), C(pending, deps=[A]) no banco
    When controller muda A -> done
    Then mock_task_list.moves contem ("B", Sector.WAITING) e ("C", Sector.WAITING)
    And a propagacao usou move_card_to_sector (nao refresh completo) — abaixo do threshold
    """
    from task_manager_desktop.controllers.change_status_controller import ChangeStatusController
    from task_manager_desktop.core.models import Sector, Task

    repo = repo_factory
    task_a = Task(id="aaa", title="A", deps=[], order_index=1)
    task_b = Task(id="bbb", title="B", deps=["aaa"], order_index=2)
    task_c = Task(id="ccc", title="C", deps=["aaa"], order_index=3)
    repo.create(task_a)
    repo.create(task_b)
    repo.create(task_c)

    class _NoopError:
        def show_io_error(self, *a, **kw):
            pass

    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: {t.id: t for t in repo.list_active()},
        error_handler=_NoopError(),
        refresh_card=lambda t: None,
        task_list=mock_task_list,
    )

    ctrl.change_status(task_a, "done")

    move_ids = {m[0] for m in mock_task_list.moves}
    move_map = {m[0]: m[1] for m in mock_task_list.moves}

    assert "bbb" in move_ids, f"B nao foi movido. moves={mock_task_list.moves}"
    assert "ccc" in move_ids, f"C nao foi movido. moves={mock_task_list.moves}"
    assert move_map["bbb"] == Sector.WAITING
    assert move_map["ccc"] == Sector.WAITING
    assert mock_task_list.refresh_calls == 0, "nao deve usar refresh (abaixo do threshold)"


# ---------------------------------------------------------------------------
# TID-2-2-011 | covers: TASK-2/ST006
# ---------------------------------------------------------------------------


def test_zero_dependents_does_not_touch_task_list(repo_factory, mock_task_list):
    """Integration: task sem dependentes nao chama move_card_to_sector nem refresh extra.

    Given uma task A isolada (sem deps reversas)
    When controller muda A -> done
    Then mock_task_list.moves esta vazio
    And refresh nao foi chamado por causa de propagacao
    """
    from task_manager_desktop.controllers.change_status_controller import ChangeStatusController
    from task_manager_desktop.core.models import Task

    repo = repo_factory
    task_z = Task(id="zzz", title="Z", deps=[], order_index=1)
    repo.create(task_z)

    class _NoopError:
        def show_io_error(self, *a, **kw):
            pass

    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: {t.id: t for t in repo.list_active()},
        error_handler=_NoopError(),
        refresh_card=lambda t: None,
        task_list=mock_task_list,
    )

    ctrl.change_status(task_z, "done")

    assert mock_task_list.moves == []
    assert mock_task_list.refresh_calls == 0


# ---------------------------------------------------------------------------
# TID-2-2-012 | covers: TASK-2/ST006, AC-T-006
# ---------------------------------------------------------------------------


def test_threshold_triggers_full_refresh(repo_factory, mock_task_list):
    """Integration: numero de dependentes acima do threshold dispara refresh completo (AC-T-006).

    Given task A com N >= threshold dependentes diretos (canonico = 20)
    When controller muda A -> done
    Then mock_task_list.refresh_calls == 1
    And mock_task_list.moves esta vazio (nao foi chamada per-card)
    """
    from task_manager_desktop.controllers.change_status_controller import ChangeStatusController
    from task_manager_desktop.core.constants import PROPAGATION_THRESHOLD as _PROPAGATION_THRESHOLD
    from task_manager_desktop.core.models import Task

    repo = repo_factory
    task_a = Task(id="aaa", title="A", deps=[], order_index=1)
    repo.create(task_a)

    # Create threshold+1 dependents
    dep_tasks = []
    for i in range(_PROPAGATION_THRESHOLD + 1):
        t = Task(id=f"d{i:02d}", title=f"D{i}", deps=["aaa"], order_index=i + 2)
        repo.create(t)
        dep_tasks.append(t)

    class _NoopError:
        def show_io_error(self, *a, **kw):
            pass

    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: {t.id: t for t in repo.list_active()},
        error_handler=_NoopError(),
        refresh_card=lambda t: None,
        task_list=mock_task_list,
    )

    ctrl.change_status(task_a, "done")

    assert mock_task_list.refresh_calls == 1, f"refresh deveria ser chamado 1 vez, foi {mock_task_list.refresh_calls}"
    assert mock_task_list.moves == [], f"move_card_to_sector nao deve ser chamado. moves={mock_task_list.moves}"


# ---------------------------------------------------------------------------
# TID-2-2-013 | covers: TASK-2/ST006, AC-T-008
# ---------------------------------------------------------------------------


def test_error_path_does_not_propagate(repo_factory, mock_task_list, monkeypatch):
    """Integration: erro I/O em update_status NAO dispara propagacao (AC-T-008).

    Given task A com dependentes diretos B, C
    When update_status falha com sqlite3.OperationalError
    Then mock_task_list.moves esta vazio
    And nenhuma chamada de refresh por propagacao
    And o erro sobe para o ErrorHandler (nao silenciado)
    """
    from task_manager_desktop.controllers.change_status_controller import ChangeStatusController
    from task_manager_desktop.core.models import Task

    repo = repo_factory
    task_a = Task(id="aaa", title="A", deps=[], order_index=1)
    task_b = Task(id="bbb", title="B", deps=["aaa"], order_index=2)
    repo.create(task_a)
    repo.create(task_b)

    error_calls: list = []

    class _RecordingError:
        def show_io_error(self, msg, path):
            error_calls.append((msg, path))

    # Patch update_status to raise OperationalError
    monkeypatch.setattr(repo, "update_status", lambda *a, **kw: (_ for _ in ()).throw(sqlite3.OperationalError("disk full")))

    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: {t.id: t for t in repo.list_active()},
        error_handler=_RecordingError(),
        refresh_card=lambda t: None,
        task_list=mock_task_list,
    )

    ctrl.change_status(task_a, "done")

    assert mock_task_list.moves == [], "propagacao NAO deve ocorrer em path de erro"
    assert mock_task_list.refresh_calls == 0
    assert len(error_calls) == 1, "erro deve ter sido reportado ao error_handler"


# ---------------------------------------------------------------------------
# TID-2-2-014 | covers: TASK-2/ST006
# ---------------------------------------------------------------------------


def test_revert_does_not_propagate(repo_factory, mock_task_list, monkeypatch):
    """Integration: revert done -> pending re-bloqueia dependentes (propagacao executa mas resultado e BLOCKED).

    Given task A done com dependente B em Fila (B.deps=[A])
    When controller muda A -> pending
    Then mock_task_list.moves contem ("B", Sector.BLOCKED) — B re-bloqueada
    And refresh NAO e chamado (abaixo do threshold)
    """
    from task_manager_desktop.controllers.change_status_controller import ChangeStatusController
    from task_manager_desktop.core.models import Sector, Status, Task

    repo = repo_factory
    # A starts as done, B depends on A (currently in WAITING since A was done)
    task_a = Task(id="aaa", title="A", deps=[], order_index=1)
    task_b = Task(id="bbb", title="B", deps=["aaa"], order_index=2)
    repo.create(task_a)
    repo.create(task_b)

    # Mark A as done in DB first
    from datetime import datetime, timezone
    repo.update_status("aaa", Status.DONE, datetime.now(timezone.utc).replace(tzinfo=None))
    task_a.status = Status.DONE

    class _NoopError:
        def show_io_error(self, *a, **kw):
            pass

    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: {t.id: t for t in repo.list_active()},
        error_handler=_NoopError(),
        refresh_card=lambda t: None,
        task_list=mock_task_list,
    )

    # Revert A from done to pending
    ctrl.change_status(task_a, "pending")

    # B should be moved to BLOCKED (A is now pending, so B has an open dep)
    move_map = {m[0]: m[1] for m in mock_task_list.moves}
    assert "bbb" in move_map, f"B deve ser movida. moves={mock_task_list.moves}"
    assert move_map["bbb"] == Sector.BLOCKED
    assert mock_task_list.refresh_calls == 0
