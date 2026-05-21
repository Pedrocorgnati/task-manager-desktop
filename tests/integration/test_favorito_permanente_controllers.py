# suite: integration | loop: 05-20-decisoes-favorito-permanente-task-manager | task: 009
# covers: source.md secao 3.5 — Controllers create/edit, favorito/permanente
"""Testes do contrato da secao 3.5: boundary de favorito/permanente, status
default/invalido e recomputo de setor nos controllers create e edit.

NAO e tdd-locked: arquivo novo do loop favorito/permanente, fora do escopo
das suites lockadas de TASK-1/TASK-2.
"""

from __future__ import annotations

import sqlite3

import pytest
from PySide6.QtWidgets import QDialog

from task_manager_desktop.controllers._boundary import (
    coerce_flag,
    recompute_sector,
    resolve_status,
)
from task_manager_desktop.controllers.create_task_controller import CreateTaskController
from task_manager_desktop.controllers.edit_task_controller import EditTaskController
from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.exceptions import TaskNotFoundError
from task_manager_desktop.core.models import Sector, Status, Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.task_list import TaskList

_ACCEPTED = QDialog.DialogCode.Accepted


# --------------------------------------------------------------------------
# coerce_flag — range booleano no boundary
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("value", "expected"),
    [(True, True), (False, False), (1, True), (0, False)],
)
def test_coerce_flag_accepts_valid_range(value, expected):
    assert coerce_flag(value, "favorito") is expected


@pytest.mark.parametrize("value", [None, "true", "1", 2, -1, 1.0, [], object()])
def test_coerce_flag_rejects_invalid_values(value):
    with pytest.raises(ValueError, match="favorito"):
        coerce_flag(value, "favorito")


# --------------------------------------------------------------------------
# resolve_status — default PENDING + erro sem fallback silencioso
# --------------------------------------------------------------------------
def test_resolve_status_defaults_to_pending_when_absent():
    assert resolve_status(None) is Status.PENDING


def test_resolve_status_accepts_status_and_valid_str():
    assert resolve_status(Status.DONE) is Status.DONE
    assert resolve_status("in_progress") is Status.IN_PROGRESS


@pytest.mark.parametrize("value", ["bogus", "DONE", "", 3, True])
def test_resolve_status_rejects_invalid_without_silent_fallback(value):
    with pytest.raises(ValueError):
        resolve_status(value)


# --------------------------------------------------------------------------
# Fixtures e fakes de dialog (mesmo padrao das suites de controller)
# --------------------------------------------------------------------------
@pytest.fixture
def env(qtbot, tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    repo = TaskRepository(conn, db_path=str(db_path))
    task_list = TaskList()
    qtbot.addWidget(task_list)
    return repo, task_list


def _fake_new_dialog(data: dict):
    class FakeDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, parent=None):
            pass

        def exec(self):
            return _ACCEPTED

        def get_data(self):
            return data

    return FakeDialog


def _fake_edit_dialog(data: dict):
    class FakeDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, task, parent=None):
            pass

        def exec(self):
            return _ACCEPTED

        def get_data(self):
            return data

    return FakeDialog


# --------------------------------------------------------------------------
# CreateTaskController — persiste favorito/permanente e recomputa setor
# --------------------------------------------------------------------------
def test_create_persists_favorito_permanente_and_recomputes_sector(env, monkeypatch):
    repo, task_list = env
    ctrl = CreateTaskController(repo, task_list, task_list, parent=None)

    from task_manager_desktop.controllers import create_task_controller as mod

    monkeypatch.setattr(mod, "NewTaskDialog", _fake_new_dialog({
        "title": "Permanente concluida",
        "type": TaskType.AGENT,
        "deps": [],
        "favorito": True,
        "permanente": True,
        "status": "done",
    }))

    ctrl.handle()

    tasks = repo.list_active()
    assert len(tasks) == 1
    created = tasks[0]
    assert created.favorito is True
    assert created.permanente is True
    assert created.status is Status.DONE

    # Setor recomputado pelo controller: done + permanente == PERMANENT.
    assert ctrl.last_persisted_task is not None
    assert ctrl.last_persisted_task.id == created.id
    assert ctrl.last_sector is not None
    assert ctrl.last_sector[0] is Sector.PERMANENT


def test_create_defaults_status_pending_and_flags_false(env, monkeypatch):
    repo, task_list = env
    ctrl = CreateTaskController(repo, task_list, task_list, parent=None)

    from task_manager_desktop.controllers import create_task_controller as mod

    monkeypatch.setattr(mod, "NewTaskDialog", _fake_new_dialog({
        "title": "Sem status nem flags",
        "type": TaskType.AGENT,
        "deps": [],
    }))

    ctrl.handle()

    created = repo.list_active()[0]
    assert created.status is Status.PENDING
    assert created.favorito is False
    assert created.permanente is False
    assert ctrl.last_sector[0] is Sector.WAITING


def test_create_rejects_invalid_flag_before_repo(env, monkeypatch):
    repo, task_list = env
    ctrl = CreateTaskController(repo, task_list, task_list, parent=None)

    from task_manager_desktop.controllers import create_task_controller as mod

    monkeypatch.setattr(mod, "NewTaskDialog", _fake_new_dialog({
        "title": "Flag invalida",
        "type": TaskType.AGENT,
        "deps": [],
        "favorito": "sim",
    }))

    with pytest.raises(ValueError, match="favorito"):
        ctrl.handle()
    # Nada foi escrito no repositorio — boundary barrou antes.
    assert repo.list_active() == []


def test_create_rejects_invalid_status_before_repo(env, monkeypatch):
    repo, task_list = env
    ctrl = CreateTaskController(repo, task_list, task_list, parent=None)

    from task_manager_desktop.controllers import create_task_controller as mod

    monkeypatch.setattr(mod, "NewTaskDialog", _fake_new_dialog({
        "title": "Status invalido",
        "type": TaskType.AGENT,
        "deps": [],
        "status": "concluida",
    }))

    with pytest.raises(ValueError, match="status invalido"):
        ctrl.handle()
    assert repo.list_active() == []


# --------------------------------------------------------------------------
# EditTaskController — toggle de favorito/permanente persistido + setor
# --------------------------------------------------------------------------
def test_edit_toggles_favorito_permanente_persisted_and_recomputes_sector(env, monkeypatch):
    repo, task_list = env
    task = Task(id="t1", title="Task", type=TaskType.AGENT, deps=[], status=Status.DONE)
    repo.create(task)
    assert repo.get_by_id("t1").permanente is False

    ctrl = EditTaskController(repo, task_list, task_list, parent=None)

    from task_manager_desktop.controllers import edit_task_controller as mod

    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "Task",
        "type": TaskType.AGENT,
        "deps": [],
        "favorito": True,
        "permanente": True,
    }))

    ctrl.handle_edit(task)

    persisted = repo.get_by_id("t1")
    assert persisted.favorito is True
    assert persisted.permanente is True

    # Setor recomputado pelo controller apos o toggle: done + permanente.
    assert ctrl.last_sector is not None
    assert ctrl.last_sector[0] is Sector.PERMANENT

    # Toggle de volta: permanente=False recoloca a task no setor DONE.
    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "Task",
        "type": TaskType.AGENT,
        "deps": [],
        "permanente": False,
    }))
    ctrl.handle_edit(persisted)

    assert repo.get_by_id("t1").permanente is False
    assert ctrl.last_sector[0] is Sector.DONE


def test_edit_rejects_invalid_flag_before_repo(env, monkeypatch):
    repo, task_list = env
    task = Task(id="t1", title="Task", type=TaskType.AGENT, deps=[])
    repo.create(task)

    ctrl = EditTaskController(repo, task_list, task_list, parent=None)

    from task_manager_desktop.controllers import edit_task_controller as mod

    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "Task",
        "type": TaskType.AGENT,
        "deps": [],
        "permanente": None,
    }))

    with pytest.raises(ValueError, match="permanente"):
        ctrl.handle_edit(task)
    # Valor original preservado — boundary barrou antes do UPDATE.
    assert repo.get_by_id("t1").permanente is False


def test_edit_rejects_invalid_status_before_repo(env, monkeypatch):
    repo, task_list = env
    task = Task(id="t1", title="Task", type=TaskType.AGENT, deps=[])
    repo.create(task)

    ctrl = EditTaskController(repo, task_list, task_list, parent=None)

    from task_manager_desktop.controllers import edit_task_controller as mod

    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "Task",
        "type": TaskType.AGENT,
        "deps": [],
        "status": "arquivada",
    }))

    with pytest.raises(ValueError, match="status invalido"):
        ctrl.handle_edit(task)
    assert repo.get_by_id("t1").status is Status.PENDING


# --------------------------------------------------------------------------
# AC-11 — toggle permanente=True em task oculta des-oculta quando DONE
# (source.md secao 1 decisao 9 + secao 5 AC-11)
# --------------------------------------------------------------------------
def test_edit_permanente_true_unhides_done_task(env, monkeypatch):
    """AC-11: toggle permanente=True em task DONE oculta zera hidden_at e move
    a task para o setor PERMANENT. Dirigido pelo EditTaskController."""
    repo, task_list = env
    task = Task(id="t1", title="Task", type=TaskType.AGENT, deps=[], status=Status.DONE)
    repo.create(task)
    # Simula a vassoura: a task DONE foi ocultada (hidden_at != NULL).
    repo._conn.execute(
        "UPDATE tasks SET hidden_at = ? WHERE id = ?",
        ("2026-05-20T12:00:00+00:00", "t1"),
    )
    repo._conn.commit()
    hidden_before = repo._conn.execute(
        "SELECT hidden_at FROM tasks WHERE id='t1'"
    ).fetchone()["hidden_at"]
    assert hidden_before is not None

    ctrl = EditTaskController(repo, task_list, task_list, parent=None)
    from task_manager_desktop.controllers import edit_task_controller as mod

    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "Task",
        "type": TaskType.AGENT,
        "deps": [],
        "permanente": True,
    }))
    ctrl.handle_edit(task)

    # hidden_at zerado no banco e setor recomputado para PERMANENT.
    hidden_after = repo._conn.execute(
        "SELECT hidden_at FROM tasks WHERE id='t1'"
    ).fetchone()["hidden_at"]
    assert hidden_after is None
    persisted = repo.get_by_id("t1")
    assert persisted.permanente is True
    assert ctrl.last_sector is not None
    assert ctrl.last_sector[0] is Sector.PERMANENT


def test_edit_permanente_true_preserves_hidden_at_when_not_done(env, monkeypatch):
    """AC-11 caso negativo: toggle permanente=True em task oculta NAO-DONE
    (PENDING) preserva hidden_at — a task nao se qualifica para PERMANENT."""
    repo, task_list = env
    task = Task(id="t1", title="Task", type=TaskType.AGENT, deps=[], status=Status.PENDING)
    repo.create(task)
    repo._conn.execute(
        "UPDATE tasks SET hidden_at = ? WHERE id = ?",
        ("2026-05-20T12:00:00+00:00", "t1"),
    )
    repo._conn.commit()

    ctrl = EditTaskController(repo, task_list, task_list, parent=None)
    from task_manager_desktop.controllers import edit_task_controller as mod

    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "Task",
        "type": TaskType.AGENT,
        "deps": [],
        "permanente": True,
    }))
    ctrl.handle_edit(task)

    # hidden_at preservado: status PENDING nao qualifica para PERMANENT.
    hidden_after = repo._conn.execute(
        "SELECT hidden_at FROM tasks WHERE id='t1'"
    ).fetchone()["hidden_at"]
    assert hidden_after == "2026-05-20T12:00:00+00:00"
    persisted = repo.get_by_id("t1")
    assert persisted.permanente is True


# --------------------------------------------------------------------------
# Simetria estrita create/edit
# --------------------------------------------------------------------------
def test_recompute_sector_returns_none_for_missing_task(env):
    repo, _ = env
    task, sector = recompute_sector(repo, "inexistente")
    assert task is None
    assert sector is None


# --------------------------------------------------------------------------
# Observabilidade (source.md secao 9) — evento estruturado favorito.toggle
# --------------------------------------------------------------------------
def _find_event(caplog, event_name):
    """Retorna o LogRecord do evento estruturado nomeado, ou None."""
    for record in caplog.records:
        if getattr(record, "event", None) == event_name:
            return record
    return None


def test_favorito_toggle_emits_structured_event_on_success(env, caplog):
    repo, task_list = env
    task = Task(id="t1", title="Task", type=TaskType.AGENT, deps=[])
    repo.create(task)
    ctrl = EditTaskController(repo, task_list, task_list, parent=None)

    with caplog.at_level("INFO", logger="task_manager_desktop.controllers.edit_task_controller"):
        ok = ctrl.handle_favorite_toggle(task, True)

    assert ok is True
    record = _find_event(caplog, "favorito.toggle")
    assert record is not None, "evento favorito.toggle nao emitido"
    # Todos os campos obrigatorios da secao 9 presentes.
    assert record.task_id == "t1"
    assert getattr(record, "from") is False
    assert record.to is True
    assert record.outcome == "ok"
    assert isinstance(record.latency_ms, (int, float))
    assert record.latency_ms >= 0


def test_favorito_toggle_emits_structured_event_on_error(env, caplog, monkeypatch):
    repo, task_list = env
    task = Task(id="t1", title="Task", type=TaskType.AGENT, deps=[])
    repo.create(task)
    ctrl = EditTaskController(repo, task_list, task_list, parent=None)

    # Repo levanta TaskNotFoundError: o controller deve emitir outcome=error.
    def boom(task_id, value):
        raise TaskNotFoundError(f"Task {task_id!r} nao encontrada")

    monkeypatch.setattr(repo, "update_favorito", boom)

    with caplog.at_level("INFO", logger="task_manager_desktop.controllers.edit_task_controller"):
        ok = ctrl.handle_favorite_toggle(task, True)

    assert ok is False
    record = _find_event(caplog, "favorito.toggle")
    assert record is not None, "evento favorito.toggle nao emitido no caminho de erro"
    assert record.task_id == "t1"
    assert getattr(record, "from") is False
    assert record.to is True
    assert record.outcome == "error"
    assert isinstance(record.latency_ms, (int, float))


# --------------------------------------------------------------------------
# Observabilidade — evento estruturado permanente.toggle
# --------------------------------------------------------------------------
def test_permanente_toggle_emits_structured_event_on_success(env, caplog):
    repo, task_list = env
    task = Task(id="t1", title="Task", type=TaskType.AGENT, deps=[], status=Status.PENDING)
    repo.create(task)
    ctrl = EditTaskController(repo, task_list, task_list, parent=None)

    with caplog.at_level("INFO", logger="task_manager_desktop.controllers.edit_task_controller"):
        ok = ctrl.handle_permanente_toggle(task, True)

    assert ok is True
    record = _find_event(caplog, "permanente.toggle")
    assert record is not None, "evento permanente.toggle nao emitido"
    assert record.task_id == "t1"
    assert getattr(record, "from") is False
    assert record.to is True
    assert record.outcome == "ok"
    assert hasattr(record, "triggered_sector_change")


def test_permanente_toggle_triggered_sector_change_true_on_done_task(env, caplog):
    """Toggle permanente=True numa task DONE move-a de DONE para PERMANENT:
    triggered_sector_change deve ser True (source.md secao 9)."""
    repo, task_list = env
    task = Task(id="t1", title="Task", type=TaskType.AGENT, deps=[], status=Status.DONE)
    repo.create(task)
    ctrl = EditTaskController(repo, task_list, task_list, parent=None)

    with caplog.at_level("INFO", logger="task_manager_desktop.controllers.edit_task_controller"):
        ok = ctrl.handle_permanente_toggle(task, True)

    assert ok is True
    record = _find_event(caplog, "permanente.toggle")
    assert record is not None
    assert record.triggered_sector_change is True


def test_permanente_toggle_triggered_sector_change_false_on_pending_task(env, caplog):
    """Toggle permanente=True numa task PENDING NAO muda o setor (permanente so
    influencia DONE): triggered_sector_change deve ser False."""
    repo, task_list = env
    task = Task(id="t1", title="Task", type=TaskType.AGENT, deps=[], status=Status.PENDING)
    repo.create(task)
    ctrl = EditTaskController(repo, task_list, task_list, parent=None)

    with caplog.at_level("INFO", logger="task_manager_desktop.controllers.edit_task_controller"):
        ok = ctrl.handle_permanente_toggle(task, True)

    assert ok is True
    record = _find_event(caplog, "permanente.toggle")
    assert record is not None
    assert record.triggered_sector_change is False


def test_permanente_toggle_emits_structured_event_on_error(env, caplog, monkeypatch):
    repo, task_list = env
    task = Task(id="t1", title="Task", type=TaskType.AGENT, deps=[], status=Status.DONE)
    repo.create(task)
    ctrl = EditTaskController(repo, task_list, task_list, parent=None)

    def boom(task_id, value):
        raise TaskNotFoundError(f"Task {task_id!r} nao encontrada")

    monkeypatch.setattr(repo, "update_permanente", boom)

    with caplog.at_level("INFO", logger="task_manager_desktop.controllers.edit_task_controller"):
        ok = ctrl.handle_permanente_toggle(task, True)

    assert ok is False
    record = _find_event(caplog, "permanente.toggle")
    assert record is not None, "evento permanente.toggle nao emitido no caminho de erro"
    assert record.outcome == "error"
    # triggered_sector_change e computado ANTES do persist — continua valido.
    assert record.triggered_sector_change is True


# --------------------------------------------------------------------------
# Autosave callback guarantee (source.md AC-14) — toggle nunca propaga excecao
# --------------------------------------------------------------------------
def test_favorito_toggle_never_propagates_unexpected_exception(env, monkeypatch, caplog):
    """Erro inesperado (nao-sqlite) no persist nao pode escapar do controller:
    o card depende do retorno bool para destravar a estrela."""
    repo, task_list = env
    task = Task(id="t1", title="Task", type=TaskType.AGENT, deps=[])
    repo.create(task)
    ctrl = EditTaskController(repo, task_list, task_list, parent=None)

    def boom(task_id, value):
        raise RuntimeError("falha inesperada do driver")

    monkeypatch.setattr(repo, "update_favorito", boom)

    with caplog.at_level("INFO", logger="task_manager_desktop.controllers.edit_task_controller"):
        ok = ctrl.handle_favorite_toggle(task, True)

    # Retorno bool garantido (nenhuma excecao escapou).
    assert ok is False
    # Excecao logada com task_id, nunca engolida em silencio.
    assert any(
        rec.levelname == "ERROR" and getattr(rec, "task_id", None) == "t1"
        for rec in caplog.records
    )
    # Evento estruturado ainda emitido com outcome=error.
    record = _find_event(caplog, "favorito.toggle")
    assert record is not None
    assert record.outcome == "error"


def test_permanente_toggle_never_propagates_unexpected_exception(env, monkeypatch, caplog):
    repo, task_list = env
    task = Task(id="t1", title="Task", type=TaskType.AGENT, deps=[], status=Status.DONE)
    repo.create(task)
    ctrl = EditTaskController(repo, task_list, task_list, parent=None)

    def boom(task_id, value):
        raise RuntimeError("falha inesperada do driver")

    monkeypatch.setattr(repo, "update_permanente", boom)

    with caplog.at_level("INFO", logger="task_manager_desktop.controllers.edit_task_controller"):
        ok = ctrl.handle_permanente_toggle(task, True)

    assert ok is False
    record = _find_event(caplog, "permanente.toggle")
    assert record is not None
    assert record.outcome == "error"


# --------------------------------------------------------------------------
# Rowcount-aware error handling (source.md secao 3.5 / contrato repo)
# --------------------------------------------------------------------------
def test_edit_persist_aborts_when_repo_raises_task_not_found(env, monkeypatch):
    """repo.update levanta TaskNotFoundError (rowcount 0): o _persist deve
    abortar (retornar False) e nao tratar a task sumida como sucesso."""
    repo, task_list = env
    task = Task(id="t1", title="Task", type=TaskType.AGENT, deps=[])
    repo.create(task)
    ctrl = EditTaskController(repo, task_list, task_list, parent=None)

    def boom(task_id, **fields):
        raise TaskNotFoundError(f"Task {task_id!r} nao encontrada")

    monkeypatch.setattr(repo, "update", boom)

    from task_manager_desktop.controllers import edit_task_controller as mod

    monkeypatch.setattr(mod, "EditTaskDialog", _fake_edit_dialog({
        "title": "Task editada",
        "type": TaskType.AGENT,
        "deps": [],
    }))

    ctrl.handle_edit(task)

    # _persist abortou: last_persisted_task continua None (refresh otimista
    # nao aconteceu).
    assert ctrl.last_persisted_task is None


def test_change_status_aborts_when_repo_raises_task_not_found(env, monkeypatch):
    """ChangeStatusController: repo.update_status levanta TaskNotFoundError —
    a mutacao otimista em memoria deve ser abortada (status nao muda)."""
    from task_manager_desktop.controllers.change_status_controller import (
        ChangeStatusController,
    )

    repo, task_list = env
    task = Task(id="t1", title="Task", type=TaskType.AGENT, deps=[], status=Status.PENDING)
    repo.create(task)

    errors = []

    class _Errors:
        def show_io_error(self, message, db_path):
            errors.append((message, db_path))

    refreshed = []

    ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: {t.id: t for t in repo.list_active()},
        error_handler=_Errors(),
        refresh_card=lambda t: refreshed.append(t),
        task_list=None,
    )

    def boom(task_id, status, completed_at):
        raise TaskNotFoundError(f"Task {task_id!r} nao encontrada")

    monkeypatch.setattr(repo, "update_status", boom)

    ctrl.change_status(task, "done")

    # Mutacao otimista abortada: o objeto Task em memoria NAO foi promovido a DONE.
    assert task.status is Status.PENDING
    # Erro surfado para o usuario (Zero Silencio).
    assert len(errors) == 1
