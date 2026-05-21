from __future__ import annotations

import sqlite3

import pytest
from PySide6.QtCore import Qt

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Subtask, Task
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui import subtask_pane as subtask_pane_mod
from task_manager_desktop.ui.subtask_pane import SubtaskPane


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    run_migrations(c)
    yield c
    c.close()


@pytest.fixture
def repo(conn):
    return TaskRepository(conn, db_path=":memory:")


def test_clear_done_button_is_disabled_without_completed_subtasks(qtbot, repo):
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="A0", state=0))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)

    pane.set_task(task)

    assert not pane.btn_clear_done.isEnabled()
    assert "Nenhuma subtask concluída" in pane.btn_clear_done.toolTip()


def test_clear_done_button_deletes_only_selected_task_completed_subtasks(qtbot, repo):
    task_a = Task(id="a", title="A")
    task_b = Task(id="b", title="B")
    repo.create(task_a)
    repo.create(task_b)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="A0", state=0))
    repo.create_subtask(Subtask(id="a2", task_id="a", text="A2", state=2))
    repo.create_subtask(Subtask(id="b2", task_id="b", text="B2", state=2))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task_a)

    assert pane.btn_clear_done.isEnabled()
    qtbot.mouseClick(pane.btn_clear_done, Qt.MouseButton.LeftButton)

    assert [s.id for s in repo.list_subtasks("a")] == ["a0"]
    assert [s.id for s in repo.list_subtasks("b")] == ["b2"]
    assert not pane.btn_clear_done.isEnabled()


def test_subtask_notes_chevron_visibility_and_autosave(qtbot, repo):
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="A0", state=0))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task)

    item = pane._list.item(0)
    row = pane._list.itemWidget(item)
    assert row.notes_toggle.isHidden() is True

    row.enterEvent(None)
    assert row.notes_toggle.isHidden() is False
    assert row.notes_toggle.property("hasNotes") is False

    qtbot.mouseClick(row.notes_toggle, Qt.MouseButton.LeftButton)
    assert row.notes_editor.isHidden() is False
    assert item.sizeHint().height() > 38

    row.notes_editor.setPlainText("nota salva")
    assert repo.list_subtasks("a")[0].notes == "nota salva"

    qtbot.mouseClick(row.notes_toggle, Qt.MouseButton.LeftButton)
    row.leaveEvent(None)
    assert row.notes_editor.isHidden() is True
    assert row.notes_toggle.isHidden() is False
    assert row.notes_toggle.property("hasNotes") is True
    assert "#111116" in row.notes_toggle.styleSheet()


def test_subtask_with_existing_notes_shows_strong_chevron_without_hover(qtbot, repo):
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="A0", state=0, notes="detalhe"))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task)

    row = pane._list.itemWidget(pane._list.item(0))

    assert row.notes_toggle.isHidden() is False
    assert row.notes_toggle.property("hasNotes") is True
    assert "#111116" in row.notes_toggle.styleSheet()


def test_subtask_inline_edit_autosaves_on_finish(qtbot, repo):
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="original", state=0))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task)

    row = pane._list.itemWidget(pane._list.item(0))
    row._begin_inline_edit()
    row._inline_edit.setText("alterado")
    row._commit_inline_edit()

    assert repo.list_subtasks("a")[0].text == "alterado"


def test_subtask_inline_edit_reverts_on_persist_failure(qtbot, repo, caplog):
    """Hardening: se a persistencia do texto inline falha, o texto e revertido
    visualmente (model + label) e o erro e logado com o subtask id — nada de
    data loss silenciosa (RAW execute sem tratamento de erro)."""
    import logging

    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="original", state=0))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task)

    # Faz o metodo do repositorio falhar como se houvesse erro de I/O.
    def _boom(_subtask_id, _text):
        raise sqlite3.OperationalError("disk I/O error")

    repo.update_subtask_text = _boom  # type: ignore[method-assign]

    row = pane._list.itemWidget(pane._list.item(0))
    row._begin_inline_edit()
    row._inline_edit.setText("alterado")

    with caplog.at_level(logging.ERROR, logger="task_manager_desktop.ui.subtask_pane"):
        row._commit_inline_edit()

    # Texto revertido no modelo e no label — sem perda silenciosa.
    assert row._subtask.text == "original"
    assert row.label.text() == "original"

    # Erro logado com o subtask id.
    failure_logs = [
        rec.getMessage()
        for rec in caplog.records
        if "inline_edit_persist_failed" in rec.getMessage()
    ]
    assert len(failure_logs) == 1
    assert "subtask_id=a0" in failure_logs[0]

    # Indicacao de erro discreta: borda vermelha temporaria no card.
    assert "#EF4444" in row._card.styleSheet()


def test_subtask_inline_edit_uses_repository_method(qtbot, repo):
    """Hardening: o commit inline persiste via repo.update_subtask_text
    (metodo do repositorio), nao via RAW repo._conn.execute."""
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="original", state=0))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task)

    calls: list[tuple[str, str]] = []
    orig = repo.update_subtask_text

    def _spy(subtask_id, text):
        calls.append((subtask_id, text))
        return orig(subtask_id, text)

    repo.update_subtask_text = _spy  # type: ignore[method-assign]

    row = pane._list.itemWidget(pane._list.item(0))
    row._begin_inline_edit()
    row._inline_edit.setText("via repo")
    row._commit_inline_edit()

    assert calls == [("a0", "via repo")]
    assert repo.list_subtasks("a")[0].text == "via repo"


def test_subtask_pane_width_is_stable_with_or_without_subtasks(qtbot, repo):
    empty_task = Task(id="empty", title="Empty")
    filled_task = Task(id="filled", title="Filled")
    repo.create(empty_task)
    repo.create(filled_task)
    repo.create_subtask(
        Subtask(
            id="s-long",
            task_id="filled",
            text="Subtask com texto longo suficiente para quebrar linha sem mudar largura",
            state=0,
        )
    )
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)

    pane.set_task(empty_task)
    empty_width = (pane.minimumWidth(), pane.maximumWidth())

    pane.set_task(filled_task)

    assert pane.property("testid") == "subtask-pane"
    assert (pane.minimumWidth(), pane.maximumWidth()) == empty_width


def test_subtask_title_renders_in_body_before_cards(qtbot, repo):
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="A0", state=0))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)

    pane.set_task(task)

    assert pane._body_title.property("testid") == "subtask-pane-title"
    assert pane._body_title.text() == "Subtasks #a"
    assert pane._layout.indexOf(pane._body_title) < pane._layout.indexOf(pane._list)
    assert pane._header_layout.indexOf(pane._body_title) == -1


def test_subtask_card_width_is_reduced_inside_fixed_pane(qtbot, repo):
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="A0", state=0))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)

    pane.set_task(task)

    row = pane._list.itemWidget(pane._list.item(0))
    assert row._card.width() == row._card.minimumWidth()
    assert row._card.maximumWidth() == row._card.minimumWidth()
    assert row._card.width() < pane.width()


def test_long_subtask_sizehint_grows_and_survives_inline_edit(qtbot, repo):
    """AC-5: subtask >300 chars nao trunca antes nem depois da edicao inline."""
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="curto", state=0))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task)

    long_text = ("palavra " * 45).strip()
    assert len(long_text) > 300

    item = pane._list.item(0)
    short_height = item.sizeHint().height()

    # antes da edicao: a medicao do texto longo ja deve exceder a do texto curto
    assert pane._measure_subtask_text_height(long_text) > pane._measure_subtask_text_height(
        "curto"
    )

    row = pane._list.itemWidget(item)
    row._begin_inline_edit()
    row._inline_edit.setText(long_text)
    row._commit_inline_edit()

    # depois da edicao: sizeHint recalculado cresceu e o texto persistiu integro
    grown_height = item.sizeHint().height()
    assert grown_height > short_height
    assert repo.list_subtasks("a")[0].text == long_text
    assert grown_height >= pane._measure_subtask_text_height(long_text)


def test_subtask_row_height_falls_back_without_qapplication(qtbot, repo, monkeypatch):
    """AC-5 ponto 3: sem QApplication ativa, altura cai para a constante documentada."""
    task = Task(id="a", title="A")
    repo.create(task)
    repo.create_subtask(Subtask(id="a0", task_id="a", text="A0", state=0))
    pane = SubtaskPane(repo)
    qtbot.addWidget(pane)
    pane.set_task(task)

    long_text = ("palavra " * 45).strip()
    monkeypatch.setattr(
        subtask_pane_mod.QApplication, "instance", staticmethod(lambda: None)
    )

    assert (
        pane._measure_subtask_text_height(long_text)
        == subtask_pane_mod.SUBTASK_FALLBACK_HEIGHT
    )
    assert (
        pane._row_height(long_text)
        == subtask_pane_mod.SUBTASK_FALLBACK_HEIGHT
        + subtask_pane_mod._SUBTASK_ROW_VPADDING
    )
