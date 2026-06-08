"""Regressão: notas perdidas ao trocar de card e voltar.

Bug original: o MarkdownReader persiste as notas no banco (save implícito ao
trocar de card, ou Ctrl+S), mas o TaskList mantém os objetos Task em cache
(self._tasks e dentro de cada TaskCard). Sem reconciliar esse cache via o
sinal notes_saved, re-selecionar o mesmo card re-emite o Task antigo e o editor
recarrega o texto pré-edição — o usuário "perde tudo que escreveu".

Estes testes fixam o wiring reader.notes_saved -> task_list.sync_task_notes
feito no app.py e o método sync_task_notes do TaskList.
"""
from __future__ import annotations

import pytest

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Status, Task
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.markdown_reader import MarkdownReader
from task_manager_desktop.ui.task_card import TaskCard
from task_manager_desktop.ui.task_list import TaskList


@pytest.fixture
def repo(in_memory_db):
    run_migrations(in_memory_db)
    return TaskRepository(in_memory_db, db_path=":memory:")


def _make_task(repo: TaskRepository, *, tid: str, notes: str = "") -> Task:
    t = Task(
        id=tid,
        title=f"Task {tid}",
        status=Status.PENDING,
        deps=[],
        notes=notes,
        order_index=1,
        created_at="2026-05-17T10:00:00",
    )
    repo.create(t)
    return t


def _card_for(task_list: TaskList, task_id: str) -> TaskCard:
    for card in task_list._cards:
        if isinstance(card, TaskCard) and card._task.id == task_id:
            return card
    raise AssertionError(f"card {task_id} não encontrado")


@pytest.fixture
def wired(qtbot, repo):
    """TaskList + MarkdownReader conectados como no app.py."""
    task_a = _make_task(repo, tid="ta", notes="# Original")
    task_b = _make_task(repo, tid="tb", notes="# Nota B")

    task_list = TaskList()
    qtbot.addWidget(task_list)
    task_list.set_repo(repo)
    task_list.refresh(repo.list_active())

    reader = MarkdownReader(repo)
    qtbot.addWidget(reader)
    reader.show()

    # Wiring espelhando app.py.
    task_list.task_selected.connect(reader.show_task)
    reader.notes_saved.connect(task_list.sync_task_notes)

    yield task_list, reader, task_a, task_b
    reader.hide()


def test_edit_switch_back_keeps_notes(qtbot, wired, repo):
    """Editar a task A, trocar para B e voltar para A mantém o texto editado."""
    task_list, reader, task_a, task_b = wired

    # Seleciona A e edita.
    reader.show_task(task_a)
    reader._editor.setPlainText("# Texto editado")

    # Troca para B: dispara save implícito + notes_saved -> sync_task_notes.
    reader.show_task(task_b)

    # Banco persistiu.
    persisted = repo.get_by_id("ta")
    assert persisted is not None
    assert persisted.notes == "# Texto editado"

    # Cache do task_list e o card foram reconciliados (não ficaram stale).
    cached = next(t for t in task_list._tasks if t.id == "ta")
    assert cached.notes == "# Texto editado"
    assert _card_for(task_list, "ta")._task.notes == "# Texto editado"

    # Re-selecionar A (via o objeto que o card emite) recarrega o texto editado,
    # não o "# Original" pré-edição — este é o coração da regressão.
    emitted = _card_for(task_list, "ta")._task
    reader.show_task(emitted)
    assert reader._editor.toPlainText() == "# Texto editado"


def test_card_selected_signal_carries_updated_notes(qtbot, wired):
    """O sinal selected do card carrega as notas atualizadas após o save."""
    task_list, reader, task_a, task_b = wired

    reader.show_task(task_a)
    reader._editor.setPlainText("# Via sinal")
    reader.show_task(task_b)  # save implícito de A

    captured: list[Task] = []
    task_list.task_selected.connect(captured.append)

    card_a = _card_for(task_list, "ta")
    card_a.selected.emit(card_a._task)

    assert captured
    assert captured[-1].id == "ta"
    assert captured[-1].notes == "# Via sinal"


def test_sync_task_notes_updates_cache_and_card(qtbot, wired):
    """sync_task_notes atualiza tanto self._tasks quanto o card, sem rebuild."""
    task_list, reader, task_a, task_b = wired

    card_before = _card_for(task_list, "ta")
    task_list.sync_task_notes("ta", "# Direto")

    cached = next(t for t in task_list._tasks if t.id == "ta")
    assert cached.notes == "# Direto"
    # Mesma instância de card (sem rebuild) com Task atualizado.
    assert _card_for(task_list, "ta") is card_before
    assert card_before._task.notes == "# Direto"


def test_sync_task_notes_unknown_id_is_noop(qtbot, wired):
    """sync_task_notes com id inexistente não levanta erro nem altera o cache."""
    task_list, reader, task_a, task_b = wired

    notes_before = {t.id: t.notes for t in task_list._tasks}
    task_list.sync_task_notes("nao-existe", "# nada")

    assert {t.id: t.notes for t in task_list._tasks} == notes_before


def test_explicit_save_reconciles_cache(qtbot, wired, repo):
    """Save explícito (Ctrl+S/toolbar) também reconcilia o cache do task_list."""
    task_list, reader, task_a, task_b = wired

    reader.show_task(task_a)
    reader._editor.setPlainText("# Salvo explicito")

    with qtbot.waitSignal(reader.notes_saved, timeout=1000):
        reader._pane.toolbar.save_requested.emit()

    cached = next(t for t in task_list._tasks if t.id == "ta")
    assert cached.notes == "# Salvo explicito"
    assert _card_for(task_list, "ta")._task.notes == "# Salvo explicito"
