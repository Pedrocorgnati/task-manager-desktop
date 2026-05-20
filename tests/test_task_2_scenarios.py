"""BDD scenarios for module-5 TASK-2 — TrashDialog + restauração + documentação.

Cobre os critérios de aceite AC-T-001..AC-T-010:
  AC-T-001: TrashDialog renderiza lista de tasks com hidden_at IS NOT NULL
  AC-T-002: TrashItemRow exibe id, título, data (DD/MM/YYYY HH:MM) e botão "Restaurar"
  AC-T-003: Empty state quando list_trash() retorna []
  AC-T-004: Clique "Restaurar" emite signal restore_requested(task_id)
  AC-T-005: Restauração limpa hidden_at (status não muda)
  AC-T-006: Task aparece no setor correto (calculado por status + deps atuais)
  AC-T-007: TrashDialog fecha com Esc; foco retorna à MainWindow
  AC-T-008: Dialog modalidade: bloqueia MainWindow até fechar
  AC-T-009: Dialog tamanho 520x360, fixo (não redimensionável), centralizado
  AC-T-010: Falha de I/O mostra ErrorDialog; item permanece visível

Stack: pytest-qt + sqlite3 em memória
"""
from __future__ import annotations

import sqlite3
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QPushButton

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Sector, Status, Task, TaskType
from task_manager_desktop.core.sector import compute_sector
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.dialogs.trash_dialog import TrashDialog

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


def _create_done_task(
    repo: TaskRepository,
    tid: str,
    title: str = "Tarefa de teste",
    status: Status = Status.DONE,
    deps: list[str] | None = None,
) -> Task:
    """Cria task e atualiza completed_at."""
    task = Task(
        id=tid,
        title=title,
        status=status,
        type=TaskType.HUMAN,
        deps=deps or [],
        notes="",
        order_index=0,
        created_at="2026-05-17T10:00:00",
    )
    repo.create(task)
    repo.update(tid, completed_at="2026-05-17T11:30:00", status=status.value)
    return task


# ── Cenário 1: Lixeira vazia → empty state ────────────────────────────────────


def test_empty_trash_shows_empty_state(qtbot, repo):
    """[AC-T-003] Empty state shown when no tasks in trash."""
    dlg = TrashDialog(repo)
    qtbot.addWidget(dlg)

    placeholder = dlg.findChild(QLabel, "trashEmptyPlaceholder")
    assert placeholder is not None, "Placeholder de lixeira vazia não encontrado"
    assert dlg._stack.currentIndex() == 0, "Stack deveria exibir placeholder (index 0)"
    assert placeholder.text() == "A Lixeira está vazia."
    assert dlg.row_ids() == []


# ── Cenário 2: Lixeira com items → rows ───────────────────────────────────────


def test_trash_with_items_shows_rows(qtbot, repo):
    """[AC-T-001, AC-T-002] Tasks listed when trash not empty, with all fields."""
    _create_done_task(repo, "aaa", title="Task Alpha")
    _create_done_task(repo, "bbb", title="Task Beta")
    repo.hide_all_done()

    dlg = TrashDialog(repo)
    qtbot.addWidget(dlg)

    # AC-T-001: lista renderizada
    rows = dlg.findChildren(QFrame, "trashRow")
    assert len(rows) == 2, f"Esperado 2 rows, encontrado {len(rows)}"
    assert set(dlg.row_ids()) == {"aaa", "bbb"}

    # AC-T-002: cada row tem id, título, data e botão
    id_labels = dlg.findChildren(QLabel, "trashRowId")
    title_labels = dlg.findChildren(QLabel, "trashRowTitle")
    date_labels = dlg.findChildren(QLabel, "trashRowDate")
    restore_btns = dlg.findChildren(QPushButton, "trashRowRestore")

    assert any(lbl.text() == "aaa" for lbl in id_labels), "ID 'aaa' não encontrado"
    assert any("Task Alpha" in lbl.text() for lbl in title_labels), "Título não exibido"
    assert any("17/05/2026" in lbl.text() for lbl in date_labels), "Data pt-BR não exibida"
    assert len(restore_btns) == 2, "Botões 'Restaurar' ausentes"
    assert dlg._stack.currentIndex() == 1, "Stack deveria exibir lista (index 1)"


# ── Cenário 3: Restaurar task → setor correto ─────────────────────────────────


def test_restore_moves_task_to_correct_sector(qtbot, repo):
    """[AC-T-004, AC-T-005, AC-T-006] Restore emits signal, clears hidden_at, task
    retains its status (sector recalculated by caller)."""
    _create_done_task(repo, "aaa", title="Restore Test", status=Status.DONE)
    repo.hide_all_done()

    dlg = TrashDialog(repo)
    qtbot.addWidget(dlg)

    restore_btn = dlg.findChild(QPushButton, "trashRowRestore")
    assert restore_btn is not None

    # AC-T-004: signal restore_requested emitido com task_id correto
    with qtbot.waitSignal(dlg.restore_requested, timeout=500) as blocker:
        restore_btn.click()

    assert blocker.args == ["aaa"], f"Signal args errado: {blocker.args}"

    # AC-T-005: hidden_at limpo, status não muda
    restored = repo.get_by_id("aaa")
    assert restored is not None
    assert restored.hidden_at is None, "hidden_at deveria ser NULL após restore"
    assert restored.status == Status.DONE, "Status não deve mudar após restore"

    # AC-T-006: setor correto para DONE sem deps
    sector, _ = compute_sector(restored.status, has_open_deps=False)
    assert sector == Sector.DONE, f"Setor esperado DONE, obtido {sector}"

    # Row removida do dialog
    assert dlg.row_ids() == [], "Row deveria ser removida do dialog após restore"


# ── Cenário 4: Esc fecha dialog ───────────────────────────────────────────────


def test_esc_closes_dialog(qtbot, repo):
    """[AC-T-007] Pressing Esc closes the TrashDialog."""
    dlg = TrashDialog(repo)
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.waitExposed(dlg)

    qtbot.keyClick(dlg, Qt.Key.Key_Escape)
    qtbot.wait(50)

    assert not dlg.isVisible(), "Dialog deveria fechar com Esc"


# ── Cenário 5: Dialog é modal ─────────────────────────────────────────────────


def test_dialog_is_modal(qtbot, repo):
    """[AC-T-008, AC-T-009] Dialog is modal and has fixed size 520×360."""
    dlg = TrashDialog(repo)
    qtbot.addWidget(dlg)

    # AC-T-008: modalidade
    assert dlg.isModal(), "TrashDialog deve ser modal"

    # AC-T-009: tamanho fixo 520×360
    assert dlg.width() == 520, f"Largura esperada 520, obtida {dlg.width()}"
    assert dlg.height() == 360, f"Altura esperada 360, obtida {dlg.height()}"
    assert dlg.minimumWidth() == dlg.maximumWidth() == 520, "Largura deve ser fixa"
    assert dlg.minimumHeight() == dlg.maximumHeight() == 360, "Altura deve ser fixa"


# ── Cenário 6: I/O error preserva estado ─────────────────────────────────────


def test_restore_io_error_preserves_state(qtbot, repo):
    """[AC-T-010] I/O error shows ErrorDialog; item remains visible in TrashDialog."""
    _create_done_task(repo, "aaa", title="Task Persistente")
    repo.hide_all_done()

    dlg = TrashDialog(repo)
    qtbot.addWidget(dlg)

    assert "aaa" in dlg.row_ids(), "Row deveria estar visível antes do erro"

    # Simula falha de I/O no restore
    with (
        patch.object(repo, "restore", side_effect=sqlite3.OperationalError("disk I/O error")),
        patch(
            "task_manager_desktop.ui.dialogs.ErrorDialog.show_io_error",
            return_value=0,
        ) as mock_error,
    ):
        restore_btn = dlg.findChild(QPushButton, "trashRowRestore")
        assert restore_btn is not None
        restore_btn.click()

    # ErrorDialog deve ter sido chamado
    mock_error.assert_called_once()

    # Estado preservado: row ainda visível, hidden_at ainda NOT NULL
    assert "aaa" in dlg.row_ids(), "Row deve permanecer visível após falha de I/O"
    task = repo.get_by_id("aaa")
    assert task is not None
    assert task.hidden_at is not None, "hidden_at deve permanecer NOT NULL após falha"
