# suite: acceptance | module: module-2-setores-dependencias | task: TASK-1
# @tdd-unlocked: 2026-05-18 (TASK-4 corretiva; ver TDD-UNLOCK-JUSTIFICATION.md)
# covers: US-004 (cenarios 1-4) — Mudar status via segmented control no card
# TIDs: TID-2-1-001, TID-2-1-002, TID-2-1-003, TID-2-1-004
#
# BDD fonte: TASK-1.md §BDD Gherkin canonico
# Fixtures: qtbot (pytest-qt), repo_factory, make_task, read_only_db_path
# Stack: PySide6 + SQLite local (offline-first)
import os
import sqlite3
import time

import pytest

from task_manager_desktop.controllers.change_status_controller import ChangeStatusController
from task_manager_desktop.core.models import Sector, Status, Task
from task_manager_desktop.core.sector import compute_sector, count_open_deps

# ---------------------------------------------------------------------------
# Fixtures locais (complementam conftest.py raiz)
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
def make_task():
    """Factory canonica de Task com defaults sensatos."""
    from task_manager_desktop.core.models import Status

    def _factory(
        id: str = "t1",
        title: str = "Task de teste",
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
def read_only_db_path(tmp_path):
    """Cria DB temporario e seta como read-only para forcar sqlite3.OperationalError."""
    from task_manager_desktop.core.db import run_migrations

    db_path = tmp_path / "readonly.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    conn.close()
    os.chmod(str(db_path), 0o444)
    yield str(db_path)
    os.chmod(str(db_path), 0o644)


@pytest.fixture
def mock_error_handler():
    """Dummy implementando ErrorHandler Protocol; conta chamadas a show_io_error."""

    class _MockErrorHandler:
        def __init__(self):
            self.calls: list[tuple[str, str]] = []

        def show_io_error(self, message: str, db_path: str) -> None:
            self.calls.append((message, db_path))

    return _MockErrorHandler()


# ---------------------------------------------------------------------------
# TID-2-1-001 | covers: US-004#cenario-1 | bdd_type: SUCCESS
# ---------------------------------------------------------------------------


def test_done_moves_to_completed_sector_with_completed_at(
    qtbot, repo_factory, make_task, mock_error_handler
):
    """[SUCCESS] Move to done sets completed_at and goes to setor 4.

    Given task 'A' has status='in_progress' and completed_at IS NULL
    When the user clicks [D] in the segmented control of task A
    Then the SQLite row for A has status='done' and completed_at != NULL
    And the card A is rendered in setor 4 with cor neutra
    And the operation completes in <= 50ms
    """
    repo = repo_factory
    task = make_task(id="A", status=Status.IN_PROGRESS)
    repo.create(task)

    refreshed = []
    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: {t.id: t for t in repo.list_active()},
        error_handler=mock_error_handler,
        refresh_card=lambda t: refreshed.append(t),
    )

    t0 = time.perf_counter()
    ctrl.change_status(task, "done")
    elapsed_ms = (time.perf_counter() - t0) * 1000

    # DB persistence
    row = repo.get_by_id("A")
    assert row is not None
    assert row.status == Status.DONE
    assert row.completed_at is not None

    # Sector check
    sector, color = compute_sector(Status.DONE, False)
    assert sector == Sector.DONE

    # refresh_card called
    assert len(refreshed) == 1

    # Performance
    assert elapsed_ms <= 50.0, f"operation took {elapsed_ms:.2f}ms > 50ms budget"

    # No errors
    assert len(mock_error_handler.calls) == 0


# ---------------------------------------------------------------------------
# TID-2-1-002 | covers: US-004#cenario-2 | bdd_type: EDGE
# ---------------------------------------------------------------------------


def test_in_progress_on_blocked_task_accepted_gray(
    qtbot, repo_factory, make_task, mock_error_handler
):
    """[EDGE] in_progress on blocked task accepted with gray color.

    Given task 'C' has status='pending' and 1 open dep
    When the user clicks [IP] in the segmented control of task C
    Then the card C appears in setor 1 (Em execucao) with cor cinza
    And no warning dialog is shown
    """
    repo = repo_factory
    # Task A is the dependency (pending = open)
    task_a = make_task(id="A", status=Status.PENDING, order_index=1)
    repo.create(task_a)
    # Task C depends on A
    task_c = make_task(id="C", status=Status.PENDING, deps=["A"], order_index=2)
    repo.create(task_c)

    refreshed = []
    all_tasks_dict = {task_a.id: task_a, task_c.id: task_c}

    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: all_tasks_dict,
        error_handler=mock_error_handler,
        refresh_card=lambda t: refreshed.append(t),
    )
    ctrl.change_status(task_c, "in_progress")

    # Task accepted (no error dialog)
    assert len(mock_error_handler.calls) == 0

    # Status persisted
    row = repo.get_by_id("C")
    assert row is not None
    assert row.status == Status.IN_PROGRESS

    # Sector: in_progress with open dep = ACTIVE (sector 1) + GRAY color
    has_open = count_open_deps(task_c.deps, all_tasks_dict) > 0
    sector, color = compute_sector(Status.IN_PROGRESS, has_open)
    from task_manager_desktop.core.models import Color
    assert sector == Sector.ACTIVE
    assert color == Color.GRAY

    # refresh_card called
    assert len(refreshed) == 1


# ---------------------------------------------------------------------------
# TID-2-1-003 | covers: US-004#cenario-3 | bdd_type: SUCCESS
# ---------------------------------------------------------------------------


def test_in_progress_to_pending_recomputes_sector(
    qtbot, repo_factory, make_task, mock_error_handler
):
    """[SUCCESS] Move from done clears completed_at.

    Given task 'A' has status='done' and completed_at IS NOT NULL
    When the user clicks [P] in the segmented control of task A
    Then the SQLite row for A has status='pending' and completed_at IS NULL
    And the card A migrates to setor Fila (2) or Bloqueadas (3) per deps
    """
    repo = repo_factory
    task = make_task(id="A", status=Status.DONE, completed_at="2026-05-01T00:00:00")
    repo.create(task)

    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: {t.id: t for t in repo.list_active()},
        error_handler=mock_error_handler,
        refresh_card=lambda t: None,
    )
    ctrl.change_status(task, "pending")

    row = repo.get_by_id("A")
    assert row is not None
    assert row.status == Status.PENDING
    assert row.completed_at is None

    # No error
    assert len(mock_error_handler.calls) == 0

    # Sector: pending no deps = WAITING (2)
    sector, _ = compute_sector(Status.PENDING, False)
    assert sector == Sector.WAITING


# ---------------------------------------------------------------------------
# TID-2-1-004 | covers: US-004#cenario-4 | bdd_type: ERROR
# ---------------------------------------------------------------------------


def test_io_failure_reverts_segmented_control(
    qtbot, read_only_db_path, make_task, mock_error_handler
):
    """[ERROR] I/O failure reverts segmented control.

    Given the database file is read-only
    And task 'A' has status='pending' and [P] is checked
    When the user clicks [IP] in the segmented control of task A
    Then an ErrorDialog modal opens with title 'Erro de I/O' and the db_path
    And the segmented control of A visually shows [P] checked again
    And task A.status in memory remains 'pending'
    And no DB mutation persists
    """
    from task_manager_desktop.repositories.task_repository import TaskRepository

    # Open read-only DB (no write permission)
    conn = sqlite3.connect(read_only_db_path)
    conn.row_factory = sqlite3.Row
    repo = TaskRepository(conn, db_path=read_only_db_path)

    task = make_task(id="A", status=Status.PENDING)

    # Mock segmented control
    class _MockSeg:
        def __init__(self):
            self.enabled_states: list[bool] = []
            self.current_value: str | None = None

        def setEnabled(self, enabled: bool) -> None:
            self.enabled_states.append(enabled)

        def setValue(self, value: str) -> None:
            self.current_value = value

    seg = _MockSeg()

    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: {"A": task},
        error_handler=mock_error_handler,
        refresh_card=lambda t: None,
    )
    ctrl.change_status(task, "in_progress", seg)

    # Error dialog was triggered
    assert len(mock_error_handler.calls) == 1
    _, db_path_reported = mock_error_handler.calls[0]
    # TASK-4/ST010: error handler recebe basename, nao path absoluto
    assert db_path_reported == os.path.basename(read_only_db_path)

    # Segmented reverted to previous status
    assert seg.current_value == Status.PENDING.value

    # Segmented re-enabled after error
    assert seg.enabled_states[-1] is True

    # Task status in memory unchanged
    assert task.status == Status.PENDING

    conn.close()
