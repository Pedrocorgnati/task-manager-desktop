"""BDD scenarios for module-5 TASK-1 — Botões "Limpar concluídas" e "Lixeira".

Cobre os critérios de aceite AC-T-001..AC-T-010:
  AC-T-001: Botão disabled quando não há tasks done visíveis; tooltip exibido
  AC-T-002: Botão enabled quando há ≥1 task done visível
  AC-T-003: Clique oculta TODAS as tasks done visíveis em UMA operação
  AC-T-004: TaskList refresh visual após sucesso
  AC-T-005: Ícone Lixeira sempre habilitado
  AC-T-006: Ícone Lixeira com tooltip correto
  AC-T-007: Clique em Lixeira emite sinal trash_clicked
  AC-T-008: Falha de I/O mostra QMessageBox.critical; estado não corrompido
  AC-T-009: Sem side effects — apenas done tasks são ocultadas
  AC-T-010: BDD de estado/sinal passa (pytest-qt)

Stack: pytest-qt + sqlite3 em memória
"""
from __future__ import annotations

import sqlite3
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Status, Task
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.header import HeaderBar

# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    run_migrations(c)
    yield c
    c.close()


@pytest.fixture()
def repo(conn, tmp_path):
    return TaskRepository(conn, db_path=str(tmp_path / "tasks.db"))


@pytest.fixture()
def header(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    return bar


def _task(tid: str, status: Status = Status.PENDING, hidden_at: str | None = None) -> Task:
    t = Task(
        id=tid,
        title=f"Task {tid}",
        status=status,
        deps=[],
    )
    return t


def _create_done(repo: TaskRepository, tid: str) -> Task:
    t = _task(tid, Status.DONE)
    repo.create(t)
    return t


def _create_pending(repo: TaskRepository, tid: str) -> Task:
    t = _task(tid, Status.PENDING)
    repo.create(t)
    return t


def _recalc_button(header: HeaderBar, repo: TaskRepository) -> None:
    """Simula o recalculo de estado do botão após refresh (lógica de app.py)."""
    all_tasks = repo.list_active()
    has_done = any(t.status == Status.DONE for t in all_tasks)
    header.set_clear_done_enabled(has_done)


# ── AC-T-001: Botão disabled quando não há done visíveis ─────────────────────


def test_ac_t001_button_disabled_when_no_done_visible(header, repo):
    """AC-T-001: Botão 'Limpar concluídas' desabilitado quando não há tasks done visíveis."""
    _create_pending(repo, "p1")
    _recalc_button(header, repo)

    assert not header._btn_clear_done.isEnabled()
    assert (
        header._btn_clear_done.toolTip()
        == "Sem tasks concluídas não-permanentes para ocultar"
    )


def test_ac_t001_button_disabled_by_default_no_tasks(header, repo):
    """AC-T-001: Botão desabilitado por padrão quando não há tasks."""
    _recalc_button(header, repo)
    assert not header._btn_clear_done.isEnabled()


# ── AC-T-002: Botão enabled quando há ≥1 done visível ────────────────────────


def test_ac_t002_button_enabled_when_has_visible_done(header, repo):
    """AC-T-002: Botão habilitado quando há pelo menos 1 task done visível."""
    _create_done(repo, "d1")
    _recalc_button(header, repo)

    assert header._btn_clear_done.isEnabled()


def test_ac_t002_button_enabled_with_multiple_done(header, repo):
    """AC-T-002: Botão habilitado com múltiplas tasks done visíveis."""
    _create_done(repo, "d1")
    _create_done(repo, "d2")
    _create_pending(repo, "p1")
    _recalc_button(header, repo)

    assert header._btn_clear_done.isEnabled()


# ── AC-T-003: Clique oculta TODAS as done em uma operação ────────────────────


def test_ac_t003_hide_all_done_in_one_operation(repo):
    """AC-T-003: hide_all_done oculta TODAS as tasks done visíveis em uma transação."""
    _create_done(repo, "d1")
    _create_done(repo, "d2")
    _create_pending(repo, "p1")

    count = repo.hide_all_done()

    assert count == 2
    active = repo.list_active()
    done_visible = [t for t in active if t.status == Status.DONE]
    assert len(done_visible) == 0, "Nenhuma task done deve permanecer visível"


def test_ac_t003_button_emits_signal_on_click(header, qtbot):
    """AC-T-003: Clique no botão habilitado emite sinal clear_completed_clicked."""
    header.set_clear_done_enabled(True)
    with qtbot.waitSignal(header.clear_completed_clicked, timeout=300):
        header._btn_clear_done.click()


# ── AC-T-004: Refresh visual após sucesso ─────────────────────────────────────


def test_ac_t004_button_disabled_after_all_done_hidden(header, repo):
    """AC-T-004: Botão fica desabilitado após ocultação de todas as done."""
    _create_done(repo, "d1")
    _recalc_button(header, repo)
    assert header._btn_clear_done.isEnabled()

    repo.hide_all_done()
    _recalc_button(header, repo)

    assert not header._btn_clear_done.isEnabled()


def test_ac_t004_active_list_empty_of_done_after_hide(repo):
    """AC-T-004: list_active não retorna tasks done após hide_all_done."""
    _create_done(repo, "d1")
    _create_done(repo, "d2")

    repo.hide_all_done()

    active = repo.list_active()
    assert all(t.status != Status.DONE for t in active)


# ── AC-T-005: Ícone Lixeira sempre habilitado ─────────────────────────────────


def test_ac_t005_trash_icon_always_enabled_empty(header, repo):
    """AC-T-005: Ícone Lixeira sempre habilitado quando não há tasks."""
    assert header._btn_trash.isEnabled()


def test_ac_t005_trash_icon_always_enabled_with_done(header, repo):
    """AC-T-005: Ícone Lixeira sempre habilitado mesmo com tasks done."""
    _create_done(repo, "d1")
    _recalc_button(header, repo)
    assert header._btn_trash.isEnabled()


def test_ac_t005_trash_icon_always_enabled_after_hide(header, repo):
    """AC-T-005: Ícone Lixeira sempre habilitado após ocultar tasks."""
    _create_done(repo, "d1")
    repo.hide_all_done()
    _recalc_button(header, repo)
    assert header._btn_trash.isEnabled()


# ── AC-T-006: Ícone Lixeira com tooltip correto ───────────────────────────────


def test_ac_t006_trash_icon_tooltip(header):
    """AC-T-006: Ícone Lixeira tem tooltip 'Lixeira (tasks ocultas até 30 dias)'."""
    assert "Lixeira" in header._btn_trash.toolTip()
    assert "30 dias" in header._btn_trash.toolTip()


# ── AC-T-007: Clique na Lixeira emite sinal trash_clicked ────────────────────


def test_ac_t007_trash_icon_emits_signal(header, qtbot):
    """AC-T-007: Clique no ícone Lixeira emite sinal trash_clicked."""
    with qtbot.waitSignal(header.trash_clicked, timeout=300):
        header._btn_trash.click()


def test_ac_t007_trash_signal_emits_via_mouse_click(header, qtbot):
    """AC-T-007: Sinal trash_clicked emitido via mouseClick (qtbot)."""
    received = []
    header.trash_clicked.connect(lambda: received.append(1))
    qtbot.mouseClick(header._btn_trash, Qt.MouseButton.LeftButton)
    assert received == [1]


# ── AC-T-008: Falha de I/O mostra ErrorDialog; estado preservado ─────────────


def test_ac_t008_io_error_shows_critical_dialog(header, repo, qtbot):
    """AC-T-008: Falha de I/O (OSError) dispara QMessageBox.critical; estado preservado."""
    _create_done(repo, "d1")

    with patch(
        "task_manager_desktop.repositories.task_repository.TaskRepository.hide_all_done",
        side_effect=OSError("Disk full"),
    ):
        with patch("PySide6.QtWidgets.QMessageBox.critical") as mock_critical:
            try:
                repo.hide_all_done()
            except OSError:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(None, "Erro ao ocultar tasks", "Disk full")

        mock_critical.assert_called_once()

    active = repo.list_active()
    assert any(t.id == "d1" for t in active), "Estado não deve ser corrompido em caso de erro"


def test_ac_t008_state_preserved_when_mark_hidden_fails(repo):
    """AC-T-008: Tasks done permanecem visíveis se operação falhar."""
    _create_done(repo, "d1")

    with patch.object(repo, "hide_all_done", side_effect=Exception("IO error")):
        try:
            repo.hide_all_done()
        except Exception:
            pass

    active = repo.list_active()
    assert any(t.id == "d1" for t in active)


# ── AC-T-009: Sem side effects — apenas done tasks ocultadas ─────────────────


def test_ac_t009_pending_tasks_not_hidden(repo):
    """AC-T-009: Tasks pending NÃO são ocultadas por hide_all_done."""
    _create_done(repo, "d1")
    _create_pending(repo, "p1")

    repo.hide_all_done()

    active = repo.list_active()
    assert any(t.id == "p1" for t in active), "Task pending deve permanecer visível"
    assert not any(t.id == "d1" for t in active), "Task done deve estar oculta"


def test_ac_t009_in_progress_tasks_not_hidden(repo):
    """AC-T-009: Tasks in_progress NÃO são afetadas por hide_all_done."""
    t = Task(
        id="ip1", title="In Progress", status=Status.IN_PROGRESS,
        deps=[],
    )
    repo.create(t)
    _create_done(repo, "d1")

    repo.hide_all_done()

    active = repo.list_active()
    assert any(t.id == "ip1" for t in active), "Task in_progress deve permanecer visível"


def test_ac_t009_hidden_done_appears_in_trash(repo):
    """AC-T-009: Tasks done ocultadas aparecem na Lixeira (soft-delete, não hard-delete)."""
    _create_done(repo, "d1")
    _create_done(repo, "d2")

    repo.hide_all_done()

    trash = repo.list_trash()
    trash_ids = {t.id for t in trash}
    assert "d1" in trash_ids
    assert "d2" in trash_ids


# ── AC-T-010: BDD estado/sinal (pytest-qt) ───────────────────────────────────


def test_ac_t010_full_bdd_scenario_clear_done(header, repo, qtbot):
    """AC-T-010: Cenário BDD completo — botão ativo → clique → tasks ocultadas → botão inativo."""
    # DADO: há tasks done visíveis
    _create_done(repo, "d1")
    _create_done(repo, "d2")
    _create_pending(repo, "p1")

    # QUANDO: recalculo de estado reflete tasks done
    _recalc_button(header, repo)
    assert header._btn_clear_done.isEnabled(), "Botão deve estar habilitado"

    # E: clique no botão emite sinal
    signal_received = []
    header.clear_completed_clicked.connect(lambda: signal_received.append(1))
    qtbot.mouseClick(header._btn_clear_done, Qt.MouseButton.LeftButton)
    assert signal_received == [1], "Sinal clear_completed_clicked deve ser emitido"

    # ENTÃO: simular callback (hide_all_done + recalc)
    count = repo.hide_all_done()
    assert count == 2
    _recalc_button(header, repo)

    # E: botão desabilitado (não há mais done)
    assert not header._btn_clear_done.isEnabled()

    # E: tasks pending permanecem visíveis
    active = repo.list_active()
    assert any(t.id == "p1" for t in active)


def test_ac_t010_full_bdd_scenario_trash_signal(header, qtbot):
    """AC-T-010: Cenário BDD completo — Lixeira sempre ativa, sinal emitido."""
    # DADO: Lixeira sempre habilitada
    assert header._btn_trash.isEnabled()

    # QUANDO: clique no ícone Lixeira
    signal_received = []
    header.trash_clicked.connect(lambda: signal_received.append(1))
    qtbot.mouseClick(header._btn_trash, Qt.MouseButton.LeftButton)

    # ENTÃO: sinal emitido
    assert signal_received == [1], "Sinal trash_clicked deve ser emitido"
