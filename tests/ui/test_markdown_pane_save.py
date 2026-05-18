from __future__ import annotations

import sqlite3

import pytest
from PySide6.QtCore import Qt

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.exceptions import TaskNotFoundError
from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.markdown_pane import MarkdownPane


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_task(task_id: str = "t1", notes: str = "# Original") -> Task:
    return Task(
        id=task_id,
        title=f"Task {task_id}",
        status=Status.PENDING,
        type=TaskType.ONLINE,
        projeto="outros",
        deps=[],
        notes=notes,
        order_index=0,
    )


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    run_migrations(c)
    yield c
    c.close()


@pytest.fixture
def repo(conn) -> TaskRepository:
    return TaskRepository(conn, db_path=":memory:")


@pytest.fixture
def sample_task(repo) -> Task:
    task = _make_task("ta", "# Original")
    repo.create(task)
    return task


@pytest.fixture
def sample_task_b(repo) -> Task:
    task = _make_task("tb", "# Nota B")
    repo.create(task)
    return task


@pytest.fixture
def pane(qtbot, repo) -> MarkdownPane:
    w = MarkdownPane(repo=repo)
    qtbot.addWidget(w)
    return w


# ── Cenário 1: Save explícito persiste e volta ao viewer ─────────────────────


def test_explicit_save_persists_and_returns_to_viewer(qtbot, pane, repo, sample_task):
    """US-008 cenário 1: save explícito persiste e exibe viewer com conteúdo atualizado."""
    pane.show()
    pane.set_task(sample_task)
    qtbot.mouseClick(pane.btn_edit, Qt.MouseButton.LeftButton)
    pane.editor.setPlainText("# Atualizado")

    with qtbot.waitSignal(pane.notes_saved, timeout=1000) as blocker:
        pane.toolbar.save_requested.emit()

    assert blocker.args == [sample_task.id, "# Atualizado"]
    assert pane.stack.currentIndex() == 0
    persisted = repo.get_by_id(sample_task.id)
    assert persisted is not None
    assert persisted.notes == "# Atualizado"
    pane.hide()


# ── Cenário 2: Notes vazias aceitas no save ───────────────────────────────────


def test_empty_notes_accepted_on_save(qtbot, pane, repo, sample_task):
    """US-008 cenário 2: notas vazias são aceitas e viewer mostra empty state."""
    pane.show()
    pane.set_task(sample_task)
    qtbot.mouseClick(pane.btn_edit, Qt.MouseButton.LeftButton)
    pane.editor.setPlainText("")

    with qtbot.waitSignal(pane.notes_saved, timeout=1000):
        pane.toolbar.save_requested.emit()

    persisted = repo.get_by_id(sample_task.id)
    assert persisted is not None
    assert persisted.notes == ""
    assert pane.stack.currentIndex() == 0
    pane.hide()


# ── Cenário 3: Save implícito ao trocar de task ───────────────────────────────


def test_implicit_save_on_task_switch(qtbot, pane, repo, sample_task, sample_task_b):
    """US-008 cenário 3: trocar de task com mudanças pendentes salva automaticamente."""
    pane.show()
    pane.set_task(sample_task)
    qtbot.mouseClick(pane.btn_edit, Qt.MouseButton.LeftButton)
    pane.editor.setPlainText("# Implicito")

    pane.set_task(sample_task_b)

    persisted = repo.get_by_id(sample_task.id)
    assert persisted is not None
    assert persisted.notes == "# Implicito"
    assert pane.stack.currentIndex() == 0
    assert pane._current_task is not None
    assert pane._current_task.id == sample_task_b.id
    pane.hide()


# ── Cenário 4: Erro em save explícito mantém editor aberto ───────────────────


def test_explicit_save_failure_keeps_editor_open(qtbot, pane, repo, sample_task, monkeypatch):
    """US-008 cenário 4: falha de I/O no save explícito mantém editor aberto."""
    pane.show()
    pane.set_task(sample_task)
    qtbot.mouseClick(pane.btn_edit, Qt.MouseButton.LeftButton)
    pane.editor.setPlainText("# vai falhar")

    # Forçar erro no repositório
    monkeypatch.setattr(
        repo,
        "update_notes",
        lambda task_id, notes: (_ for _ in ()).throw(
            sqlite3.OperationalError("database is locked")
        ),
    )
    # Suprimir ErrorDialog para não bloquear o teste
    monkeypatch.setattr(
        "task_manager_desktop.ui.markdown_pane.MarkdownPane._show_io_error",
        lambda self, exc: None,
    )

    pane.toolbar.save_requested.emit()
    qtbot.wait(50)

    assert pane.stack.currentIndex() == 1  # editor permanece aberto
    assert pane.editor.toPlainText() == "# vai falhar"
    assert not pane.editor.isReadOnly()  # restaurado após o erro
    pane.hide()


# ── Cenário 5: Erro em save implícito mostra toast e prossegue ───────────────


def test_implicit_save_failure_shows_toast_and_proceeds(
    qtbot, pane, repo, sample_task, sample_task_b, monkeypatch
):
    """US-008 cenário 5: falha em save implícito mostra toast e carrega a nova task."""
    pane.show()
    pane.set_task(sample_task)
    qtbot.mouseClick(pane.btn_edit, Qt.MouseButton.LeftButton)
    pane.editor.setPlainText("# falha silenciosa")

    toast_messages: list[str] = []

    def _fake_show_toast(self, message: str) -> None:
        toast_messages.append(message)

    monkeypatch.setattr(
        "task_manager_desktop.ui.markdown_pane.MarkdownPane._show_toast_warning",
        _fake_show_toast,
    )
    monkeypatch.setattr(
        repo,
        "update_notes",
        lambda task_id, notes: (_ for _ in ()).throw(
            sqlite3.OperationalError("database is locked")
        ),
    )

    pane.set_task(sample_task_b)

    assert any("anterior" in m.lower() or "falha" in m.lower() for m in toast_messages)
    assert pane._current_task is not None
    assert pane._current_task.id == sample_task_b.id
    assert pane.stack.currentIndex() == 0
    pane.hide()


# ── Estado de loading do botão Salvar ────────────────────────────────────────


def test_save_btn_restored_after_successful_save(qtbot, pane, repo, sample_task):
    """AC-006: botão Salvar deve estar habilitado e com texto original após save."""
    pane.show()
    pane.set_task(sample_task)
    qtbot.mouseClick(pane.btn_edit, Qt.MouseButton.LeftButton)
    pane.editor.setPlainText("# OK")

    with qtbot.waitSignal(pane.notes_saved, timeout=1000):
        pane.toolbar.save_requested.emit()

    assert pane.toolbar.btn_save.isEnabled()
    assert pane.toolbar.btn_save.text() == "Salvar"
    assert not pane.editor.isReadOnly()
    pane.hide()
