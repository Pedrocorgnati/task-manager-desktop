# suite: unit | module: module-2-setores-dependencias | task: TASK-1 + TASK-4
# @tdd-unlocked: 2026-05-18 (TASK-4 corretiva; ver TDD-UNLOCK-JUSTIFICATION.md)
# covers: TASK-1/ST005 — ChangeStatusController logica pura
#         TASK-4/ST001, ST002, ST008, ST010 — hardening pos-PY-REVIEW
# target: task_manager_desktop/controllers/change_status_controller.py
# TIDs: TID-2-1-005, TID-2-1-006, TID-2-1-007, TID-2-1-008,
#        TID-2-1-009, TID-2-1-010, TID-2-1-011,
#        TID-2-1-016, TID-2-1-017, TID-2-1-018
from __future__ import annotations

import logging
import sqlite3
from unittest.mock import MagicMock

import pytest

from task_manager_desktop.controllers.change_status_controller import ChangeStatusController
from task_manager_desktop.core.models import Status, Task

# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_error_handler():
    """Dummy implementando ErrorHandler Protocol; conta chamadas a show_io_error."""

    class _MockErrorHandler:
        def __init__(self):
            self.calls: list[tuple[str, str]] = []

        def show_io_error(self, message: str, db_path: str) -> None:
            self.calls.append((message, db_path))

    return _MockErrorHandler()


@pytest.fixture
def mock_segmented_control():
    """Spy do StatusSegmentedControl; rastreia setEnabled e valor atual."""

    class _MockSeg:
        def __init__(self):
            self.enabled_states: list[bool] = []
            self.current_value: str | None = None

        def setEnabled(self, enabled: bool) -> None:
            self.enabled_states.append(enabled)

        def setValue(self, value: str) -> None:
            self.current_value = value

    return _MockSeg()


@pytest.fixture
def all_tasks_provider_fixture():
    """Retorna dict[str, Task] fixo para validar pureza (AC-T-004 de TASK-2)."""
    from task_manager_desktop.core.models import Status, Task

    t_a = Task(id="A", title="A", status=Status.PENDING, deps=[], order_index=1)
    t_b = Task(id="B", title="B", status=Status.PENDING, deps=["A"], order_index=2)
    t_c = Task(id="C", title="C", status=Status.IN_PROGRESS, deps=["A"], order_index=3)
    return {"A": t_a, "B": t_b, "C": t_c}


def _make_ctrl(mock_repo, mock_error_handler, refresh_cb=None, all_tasks=None, task_list=None):
    provider_calls = {"count": 0}

    def _provider():
        provider_calls["count"] += 1
        return all_tasks or {}

    ctrl = ChangeStatusController(
        repo=mock_repo,
        all_tasks_provider=_provider,
        error_handler=mock_error_handler,
        refresh_card=refresh_cb or (lambda t: None),
        task_list=task_list,
    )
    ctrl._provider_calls = provider_calls  # type: ignore[attr-defined]
    return ctrl


def _make_repo(db_path="/fake.db"):
    repo = MagicMock()
    repo.db_path = db_path
    return repo


def _make_task(status=Status.PENDING, completed_at=None, deps=None):
    return Task(id="t1", title="Test", status=status, deps=deps or [], order_index=1, completed_at=completed_at)


# ---------------------------------------------------------------------------
# TID-2-1-005 | covers: TASK-1/ST005, AC-T-001, AC-T-002
# ---------------------------------------------------------------------------


def test_pending_to_done_persists_status_and_completed_at(mock_error_handler):
    """ChangeStatusController.handle: pending->done persiste status='done' e seta completed_at != NULL."""
    repo = _make_repo()
    task = _make_task(status=Status.PENDING)

    ctrl = _make_ctrl(repo, mock_error_handler)
    ctrl.change_status(task, "done")

    repo.update_status.assert_called_once()
    args = repo.update_status.call_args
    task_id, status, completed_at = args[0]
    assert task_id == "t1"
    assert status == Status.DONE
    assert completed_at is not None
    assert task.status == Status.DONE
    assert task.completed_at is not None


# ---------------------------------------------------------------------------
# TID-2-1-006 | covers: TASK-1/ST005, AC-T-002
# ---------------------------------------------------------------------------


def test_done_to_pending_clears_completed_at(mock_error_handler):
    """ChangeStatusController.handle: done->pending limpa completed_at para NULL."""
    repo = _make_repo()
    task = _make_task(status=Status.DONE, completed_at="2026-05-01T12:00:00")

    ctrl = _make_ctrl(repo, mock_error_handler)
    ctrl.change_status(task, "pending")

    args = repo.update_status.call_args[0]
    assert args[1] == Status.PENDING
    assert args[2] is None
    assert task.completed_at is None


# ---------------------------------------------------------------------------
# TID-2-1-007 | covers: TASK-1/ST005, AC-T-002
# ---------------------------------------------------------------------------


def test_done_to_in_progress_clears_completed_at(mock_error_handler):
    """ChangeStatusController.handle: done->in_progress limpa completed_at para NULL."""
    repo = _make_repo()
    task = _make_task(status=Status.DONE, completed_at="2026-05-01T12:00:00")

    ctrl = _make_ctrl(repo, mock_error_handler)
    ctrl.change_status(task, "in_progress")

    args = repo.update_status.call_args[0]
    assert args[1] == Status.IN_PROGRESS
    assert args[2] is None


# ---------------------------------------------------------------------------
# TID-2-1-008 | covers: TASK-1/ST005, AC-T-004 — No-op quando status igual
# ---------------------------------------------------------------------------


def test_same_status_is_silent_noop_no_db_write(mock_error_handler):
    """ChangeStatusController.handle: mesmo status nao dispara nenhuma escrita no DB."""
    repo = _make_repo()
    task = _make_task(status=Status.PENDING)

    ctrl = _make_ctrl(repo, mock_error_handler)
    ctrl.change_status(task, "pending")

    repo.update_status.assert_not_called()
    assert len(mock_error_handler.calls) == 0


# ---------------------------------------------------------------------------
# TID-2-1-009 | covers: TASK-1/ST005, AC-T-008 ramo (a) — status invalido
# ---------------------------------------------------------------------------


def test_invalid_status_string_is_logged_and_noop(mock_error_handler, caplog):
    """Status invalido emite logging.warning (nao print stderr) e nao gera escrita nem crash."""
    repo = _make_repo()
    task = _make_task(status=Status.PENDING)

    ctrl = _make_ctrl(repo, mock_error_handler)
    with caplog.at_level(logging.WARNING, logger="task_manager_desktop.controllers.change_status_controller"):
        ctrl.change_status(task, "INVALID_STATUS_XYZ")

    repo.update_status.assert_not_called()
    assert len(mock_error_handler.calls) == 0
    assert any("INVALID_STATUS_XYZ" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# TID-2-1-010 | covers: TASK-1/ST005, AC-T-005 + TASK-4/ST010 (basename)
# ---------------------------------------------------------------------------


def test_repo_operational_error_triggers_show_io_error_and_refresh(
    mock_error_handler, monkeypatch
):
    """ChangeStatusController.handle: sqlite3.OperationalError chama error_handler.show_io_error e dispara refresh."""
    repo = _make_repo(db_path="/home/user/.local/share/task-manager-desktop/locked.db")
    repo.update_status.side_effect = sqlite3.OperationalError("disk I/O error")

    refreshed = []
    task = _make_task(status=Status.PENDING)
    original_status = task.status

    ctrl = _make_ctrl(repo, mock_error_handler, refresh_cb=lambda t: refreshed.append(t.id))
    ctrl.change_status(task, "done")

    assert len(mock_error_handler.calls) == 1
    msg, db_label = mock_error_handler.calls[0]
    assert "disk I/O error" in msg
    # ST010: UI ve apenas basename, nao path absoluto
    assert db_label == "locked.db"
    assert "/home/user" not in db_label
    assert refreshed == ["t1"]
    assert task.status == original_status


def test_io_error_shows_basename_not_absolute_path(mock_error_handler):
    """ST010: error_handler.show_io_error recebe basename do DB, nunca path absoluto."""
    repo = _make_repo(db_path="/var/data/secret-user/db/tm.db")
    repo.update_status.side_effect = sqlite3.OperationalError("locked")

    ctrl = _make_ctrl(repo, mock_error_handler)
    ctrl.change_status(_make_task(), "done")

    assert len(mock_error_handler.calls) == 1
    _msg, db_label = mock_error_handler.calls[0]
    assert db_label == "tm.db"
    assert "/" not in db_label


# ---------------------------------------------------------------------------
# TID-2-1-011 | covers: TASK-1/ST005, AC-T-003
# ---------------------------------------------------------------------------


def test_pending_with_open_deps_to_in_progress_recomputes_sector(
    mock_error_handler, all_tasks_provider_fixture
):
    """ChangeStatusController.handle: task com deps abertas que vai para in_progress recomputa setor corretamente."""
    repo = _make_repo()
    task_c = all_tasks_provider_fixture["C"]

    refreshed = []
    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: all_tasks_provider_fixture,
        error_handler=mock_error_handler,
        refresh_card=lambda t: refreshed.append(t.status),
    )
    ctrl.change_status(task_c, "pending")

    repo.update_status.assert_called_once()
    assert task_c.status == Status.PENDING
    assert refreshed == [Status.PENDING]


# ---------------------------------------------------------------------------
# TID-2-1-016 | covers: US-021#cenario-1 — btn_group desabilitado durante write
# ---------------------------------------------------------------------------


def test_btn_group_disabled_during_write(mock_error_handler, mock_segmented_control):
    """Durante a escrita no DB, o segmented control deve ficar desabilitado (setEnabled(False))."""
    repo = _make_repo()
    disabled_at_write_time = []

    def track_write(task_id, status, completed_at):
        disabled_at_write_time.extend(mock_segmented_control.enabled_states)

    repo.update_status.side_effect = track_write

    task = _make_task(status=Status.PENDING)
    ctrl = _make_ctrl(repo, mock_error_handler)
    ctrl.change_status(task, "done", mock_segmented_control)

    assert False in disabled_at_write_time, "segmented was never disabled before write"
    assert mock_segmented_control.enabled_states[-1] is True


# ---------------------------------------------------------------------------
# TID-2-1-017 | covers: US-021#cenario-2 — btn_group reabilitado apos erro I/O
# ---------------------------------------------------------------------------


def test_btn_group_reenabled_after_io_error(
    mock_error_handler, mock_segmented_control, monkeypatch
):
    """Apos erro de I/O, o segmented control deve ser reabilitado (setEnabled(True)) e valor revertido."""
    repo = _make_repo()
    repo.update_status.side_effect = sqlite3.OperationalError("write error")

    task = _make_task(status=Status.PENDING)
    ctrl = _make_ctrl(repo, mock_error_handler)
    ctrl.change_status(task, "done", mock_segmented_control)

    assert mock_segmented_control.enabled_states[-1] is True
    assert mock_segmented_control.current_value == Status.PENDING.value
    assert len(mock_error_handler.calls) == 1


# ---------------------------------------------------------------------------
# TID-2-1-018 | covers: US-021#cenario-3, AC-T-007 — segmented guard real
# (TASK-4/ST002: substitui o teste tautologico do _busy pelo guard real)
# ---------------------------------------------------------------------------


def test_segmented_guard_disables_before_write(mock_error_handler, mock_segmented_control):
    """Guard real: segmented.setEnabled(False) e chamado ANTES de repo.update_status.

    Em single-thread Qt, o segmented disabled bloqueia novo click do usuario
    enquanto a transacao roda. _busy permanece como guardrail defensivo
    documentado caso o controller migre para QThreadPool no futuro.
    """
    repo = _make_repo()
    enabled_order: list[bool] = []
    update_called_after_disable: list[bool] = []

    def on_update(task_id, status, completed_at):
        update_called_after_disable.append(False in mock_segmented_control.enabled_states)

    repo.update_status.side_effect = on_update
    mock_segmented_control.setEnabled = lambda v: enabled_order.append(v)  # type: ignore[method-assign]
    # rewire enabled_states for above closure
    mock_segmented_control.enabled_states = enabled_order

    task = _make_task(status=Status.PENDING)
    ctrl = _make_ctrl(repo, mock_error_handler)
    ctrl.change_status(task, "done", mock_segmented_control)

    # setEnabled chamada >= 2x: False antes do write, True depois
    assert enabled_order[0] is False, "segmented foi habilitado antes do write"
    assert enabled_order[-1] is True, "segmented nao foi reabilitado apos write"
    # E o write so aconteceu DEPOIS do disable
    assert update_called_after_disable == [True]


def test_change_status_does_not_swallow_non_db_errors(mock_error_handler):
    """TASK-4/ST001: excecoes nao-sqlite levantadas pelo refresh devem propagar."""
    repo = _make_repo()

    def boom(_task):
        raise KeyError("simulated bug in refresh callback")

    ctrl = _make_ctrl(repo, mock_error_handler, refresh_cb=boom)
    task = _make_task(status=Status.PENDING)
    with pytest.raises(KeyError, match="simulated bug"):
        ctrl.change_status(task, "done")


def test_propagation_skipped_on_io_error(mock_error_handler, all_tasks_provider_fixture):
    """TASK-4/ST008 — AC-T-008 ramo (b): em erro de I/O a propagacao nao roda.

    @pytest.mark.acceptance (referencia AC-T-008 b)
    """
    repo = _make_repo()
    repo.update_status.side_effect = sqlite3.OperationalError("locked")

    task_list_mock = MagicMock()
    task = _make_task(status=Status.PENDING)

    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: all_tasks_provider_fixture,
        error_handler=mock_error_handler,
        refresh_card=lambda t: None,
        task_list=task_list_mock,
    )
    ctrl.change_status(task, "done")

    assert task_list_mock.refresh.call_count == 0
    assert task_list_mock.move_card_to_sector.call_count == 0
    assert len(mock_error_handler.calls) == 1


def test_change_status_calls_provider_at_most_once(mock_error_handler, all_tasks_provider_fixture):
    """TASK-4/ST007: all_tasks_provider e invocado no maximo 1 vez por mudanca."""
    repo = _make_repo()
    task = _make_task(status=Status.PENDING)
    task_list_mock = MagicMock()

    ctrl = _make_ctrl(
        repo,
        mock_error_handler,
        all_tasks=all_tasks_provider_fixture,
        task_list=task_list_mock,
    )
    ctrl.change_status(task, "done")

    assert ctrl._provider_calls["count"] <= 1


def test_handle_is_alias_for_change_status(mock_error_handler):
    """handle() é alias backward-compat de change_status() — deve produzir o mesmo efeito."""
    repo = _make_repo()
    task = _make_task(status=Status.PENDING)

    ctrl = _make_ctrl(repo, mock_error_handler)
    ctrl.handle(task, "done")

    repo.update_status.assert_called_once()
    assert task.status == Status.DONE


# ---------------------------------------------------------------------------
# Setor manual "Em preparação": qualquer botao de status devolve a task ao
# fluxo normal zerando a flag em_preparacao.
# ---------------------------------------------------------------------------


def test_status_change_clears_em_preparacao(mock_error_handler):
    """Mudar de status (pending->in_progress) zera em_preparacao no repo e em memoria."""
    repo = _make_repo()
    task = _make_task(status=Status.PENDING)
    task.em_preparacao = True

    ctrl = _make_ctrl(repo, mock_error_handler)
    ctrl.change_status(task, "in_progress")

    repo.update_em_preparacao.assert_called_once_with("t1", False)
    repo.update_status.assert_called_once()
    assert task.em_preparacao is False
    assert task.status == Status.IN_PROGRESS


def test_same_status_click_still_clears_em_preparacao_and_refreshes(mock_error_handler):
    """Reclicar o status atual nao muda status, mas ainda tira a task de "Em preparação"."""
    repo = _make_repo()
    task = _make_task(status=Status.PENDING)
    task.em_preparacao = True
    refreshed: list[str] = []

    ctrl = _make_ctrl(repo, mock_error_handler, refresh_cb=lambda t: refreshed.append(t.id))
    ctrl.change_status(task, "pending")

    repo.update_em_preparacao.assert_called_once_with("t1", False)
    repo.update_status.assert_not_called()  # status inalterado
    assert task.em_preparacao is False
    assert refreshed == ["t1"]  # card re-renderizado para sair do setor verde


def test_status_change_without_preparacao_does_not_touch_flag(mock_error_handler):
    """Task fora de "Em preparação" nao dispara update_em_preparacao."""
    repo = _make_repo()
    task = _make_task(status=Status.PENDING)  # em_preparacao default False

    ctrl = _make_ctrl(repo, mock_error_handler)
    ctrl.change_status(task, "done")

    repo.update_em_preparacao.assert_not_called()
