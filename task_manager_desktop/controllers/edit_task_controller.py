from __future__ import annotations

import logging
import sqlite3
import time

from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QApplication

from task_manager_desktop.controllers._boundary import (
    coerce_flag,
    recompute_sector,
    resolve_status,
)
from task_manager_desktop.core.cycles import resolve_cycles
from task_manager_desktop.core.exceptions import TaskNotFoundError
from task_manager_desktop.core.models import Sector, Status, Task
from task_manager_desktop.core.sector import compute_sector, has_open_deps_for
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.dialogs import ErrorDialog
from task_manager_desktop.ui.dialogs.edit_task_dialog import EditTaskDialog
from task_manager_desktop.ui.task_list import TaskList
from task_manager_desktop.ui.toast import ToastWidget

_LOG = logging.getLogger(__name__)


class EditTaskController(QObject):
    def __init__(
        self,
        repo: TaskRepository,
        task_list: TaskList,
        main_window: QObject,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self._task_list = task_list
        self._main_window = main_window
        # Resultado do ultimo persist bem-sucedido: a task recarregada e o
        # setor recomputado, expostos para a UI consumir sem recalcular.
        self._last_persisted_task: Task | None = None
        self._last_sector: tuple[Sector, str] | None = None

    @property
    def last_persisted_task(self) -> Task | None:
        """Task recarregada apos o ultimo `_persist` bem-sucedido (ou None)."""
        return self._last_persisted_task

    @property
    def last_sector(self) -> tuple[Sector, str] | None:
        """Setor/cor recomputados apos o ultimo `_persist` bem-sucedido."""
        return self._last_sector

    def handle_edit(self, task: Task) -> None:
        from PySide6.QtWidgets import QDialog, QWidget

        parent_widget = self._main_window if isinstance(self._main_window, QWidget) else None
        dialog = EditTaskDialog(task, parent_widget)
        persisted = [False]

        def submit(data: dict) -> bool:
            persisted[0] = True
            return self._persist(task, data, parent_widget)

        dialog.submit_handler = submit
        result = dialog.exec()
        # Compatibilidade com fakes legados que retornam Accepted sem invocar submit_handler.
        if result == QDialog.DialogCode.Accepted and not persisted[0]:
            self._persist(task, dialog.get_data(), parent_widget)

    def _persist(self, task: Task, data: dict, parent_widget) -> bool:
        # US-020 c3: retornar False mantem dialog aberto pra nova tentativa.
        all_tasks = self._repo.list_active()
        all_tasks_dict = {t.id: t for t in all_tasks}

        clean_deps, cycle_desc = resolve_cycles(task.id, data["deps"], all_tasks_dict)

        # Boundary validation (source.md secao 3.5): simetria estrita com a
        # criacao — favorito/permanente e status sao validados ANTES de qualquer
        # escrita. Valor invalido levanta ValueError aqui, sem fallback silencioso.
        # Cada campo so e atualizado quando o caller efetivamente o forneceu, para
        # nao sobrescrever o valor atual da task com um default.
        update_fields: dict[str, object] = {
            "title": data["title"],
            "type": data["type"],
            "deps": clean_deps,
        }
        if "favorito" in data:
            update_fields["favorito"] = coerce_flag(data["favorito"], "favorito")
        if "permanente" in data:
            update_fields["permanente"] = coerce_flag(data["permanente"], "permanente")
        if "status" in data:
            update_fields["status"] = resolve_status(data["status"])

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._repo.update(task.id, **update_fields)
        except TaskNotFoundError as exc:
            # A task sumiu do banco entre abrir o dialog e salvar (corrida ou
            # delecao concorrente). repo.update levanta TaskNotFoundError quando
            # o UPDATE afeta 0 linhas. Abortar o refresh otimista: tratar uma
            # task sumida como sucesso mascararia uma escrita que nao aconteceu
            # (source.md secao 3.5).
            _LOG.warning(
                "edit.persist abortado: task %s nao encontrada no UPDATE: %s",
                task.id,
                exc,
                extra={"task_id": task.id},
            )
            ErrorDialog.show_io_error(parent_widget, exc, str(self._repo.db_path))
            return False
        except sqlite3.Error as exc:
            # sqlite3.IntegrityError (UPDATE afetou >1 linha) e demais erros de
            # I/O do SQLite. IntegrityError e subclasse de sqlite3.Error.
            _LOG.error(
                "edit.persist falhou para task %s: %s",
                task.id,
                exc,
                extra={"task_id": task.id, "db_path": self._repo.db_path},
            )
            ErrorDialog.show_io_error(parent_widget, exc, str(self._repo.db_path))
            return False
        finally:
            QApplication.restoreOverrideCursor()

        if cycle_desc and parent_widget:
            toast = ToastWidget(parent_widget)
            toast.show_message(
                "Ciclo de dependência detectado. Dependência mais antiga removida automaticamente."
            )

        # Recomputa o setor da task editada e expoe para a UI consumir.
        self._last_persisted_task, self._last_sector = recompute_sector(self._repo, task.id)

        self._task_list.refresh(self._repo.list_active())
        return True

    def handle_inline_title_edit(self, task: Task, new_title: str) -> None:
        from PySide6.QtWidgets import QWidget

        parent_widget = self._main_window if isinstance(self._main_window, QWidget) else None
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._repo.update(task.id, title=new_title)
        except TaskNotFoundError as exc:
            # Task sumiu durante a edicao inline: abortar o refresh otimista.
            _LOG.warning(
                "inline_title_edit abortado: task %s nao encontrada: %s",
                task.id,
                exc,
                extra={"task_id": task.id},
            )
            ErrorDialog.show_io_error(parent_widget, exc, str(self._repo.db_path))
            return
        except sqlite3.Error as exc:
            _LOG.error(
                "inline_title_edit falhou para task %s: %s",
                task.id,
                exc,
                extra={"task_id": task.id, "db_path": self._repo.db_path},
            )
            ErrorDialog.show_io_error(parent_widget, exc, str(self._repo.db_path))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self._task_list.refresh(self._repo.list_active())

    def handle_favorite_toggle(self, task: Task, value: bool) -> bool:
        """Persiste o flag favorito da task. Retorna True se salvou, False senao.

        Chamado pelo autosave debounced da estrela do TaskCard (source.md AC-14).
        Em sucesso, dispara o refresh da lista (que reordena o setor pela nova
        flag favorito). Em falha, mostra toast e retorna False para o card
        reverter visualmente — nunca falha silenciosa (source.md rejeicao #10).

        Garantia de callback (source.md secao 3.6 / AC-14): este metodo NUNCA
        propaga excecao para o caller. O TaskCard usa o valor de retorno (bool)
        para destravar a estrela (`if ok: ... else: _rollback_star()`); uma
        excecao escapando deixaria o lockout da estrela travado para sempre. O
        bloco try/except/finally garante que um bool sempre seja retornado,
        mesmo diante de erro inesperado.

        Observabilidade (source.md secao 9): emite UM evento `favorito.toggle`
        estruturado com `task_id`, `from`, `to`, `latency_ms`, `outcome`
        (`ok|error`) — o mesmo payload canonico no caminho de sucesso e de erro.
        A latencia mede o persist (`repo.update_favorito`).
        """
        from PySide6.QtWidgets import QWidget

        parent_widget = (
            self._main_window if isinstance(self._main_window, QWidget) else None
        )
        from_value = task.favorito
        start = time.perf_counter()
        outcome = "error"
        try:
            try:
                self._repo.update_favorito(task.id, value)
            except (TaskNotFoundError, sqlite3.Error) as exc:
                # Erro esperado de I/O / rowcount: toast + rollback via retorno.
                _LOG.warning(
                    "favorito.toggle falhou para task %s: %s",
                    task.id,
                    exc,
                    extra={"task_id": task.id},
                )
                if parent_widget is not None:
                    ToastWidget(parent_widget).show_message(
                        "Não foi possível salvar o favorito. Tente novamente."
                    )
                return False
            except Exception:
                # Erro inesperado: nunca engolir — logar com task_id e devolver
                # False para o card destravar a estrela (autosave callback
                # guarantee, source.md AC-14).
                _LOG.exception(
                    "favorito.toggle erro inesperado para task %s",
                    task.id,
                    extra={"task_id": task.id},
                )
                if parent_widget is not None:
                    ToastWidget(parent_widget).show_message(
                        "Não foi possível salvar o favorito. Tente novamente."
                    )
                return False
            outcome = "ok"
            self._task_list.refresh(self._repo.list_active())
            return True
        finally:
            latency_ms = round((time.perf_counter() - start) * 1000, 3)
            _LOG.info(
                "favorito.toggle",
                extra={
                    "event": "favorito.toggle",
                    "task_id": task.id,
                    "from": from_value,
                    "to": value,
                    "latency_ms": latency_ms,
                    "outcome": outcome,
                },
            )

    def handle_permanente_toggle(self, task: Task, value: bool) -> bool:
        """Persiste o flag permanente da task. Retorna True se salvou, False senao.

        Simetrico a `handle_favorite_toggle` (source.md secao 3.5). Em sucesso
        dispara o refresh da lista; em falha mostra toast e retorna False, sem
        nunca propagar excecao para o caller (mesma garantia de callback).

        Observabilidade (source.md secao 9): emite um evento `permanente.toggle`
        estruturado com `task_id`, `from`, `to`, `triggered_sector_change`
        (bool) — o mesmo payload canonico no sucesso e no erro.
        `triggered_sector_change` compara o setor da task ANTES e DEPOIS do
        toggle via `compute_sector` (com `permanente` repassado, source.md
        secao 3.2): True quando ligar/desligar permanente efetivamente move a
        task de setor (caso DONE), False caso contrario.
        """
        from PySide6.QtWidgets import QWidget

        parent_widget = (
            self._main_window if isinstance(self._main_window, QWidget) else None
        )
        from_value = task.permanente
        # Setor antes vs. depois do toggle: mesmo status e mesmas deps, so muda
        # o flag permanente. compute_sector so reage a permanente quando o
        # status e DONE (source.md secao 3.2).
        all_tasks = {t.id: t for t in self._repo.list_active()}
        open_deps = has_open_deps_for(task, all_tasks)
        sector_before, _ = compute_sector(task.status, open_deps, from_value)
        sector_after, _ = compute_sector(task.status, open_deps, value)
        triggered_sector_change = sector_before != sector_after
        outcome = "error"
        try:
            try:
                self._repo.update_permanente(task.id, value)
            except (TaskNotFoundError, sqlite3.Error) as exc:
                _LOG.warning(
                    "permanente.toggle falhou para task %s: %s",
                    task.id,
                    exc,
                    extra={"task_id": task.id},
                )
                if parent_widget is not None:
                    ToastWidget(parent_widget).show_message(
                        "Não foi possível salvar permanente. Tente novamente."
                    )
                return False
            except Exception:
                _LOG.exception(
                    "permanente.toggle erro inesperado para task %s",
                    task.id,
                    extra={"task_id": task.id},
                )
                if parent_widget is not None:
                    ToastWidget(parent_widget).show_message(
                        "Não foi possível salvar permanente. Tente novamente."
                    )
                return False
            outcome = "ok"
            self._task_list.refresh(self._repo.list_active())
            return True
        finally:
            _LOG.info(
                "permanente.toggle",
                extra={
                    "event": "permanente.toggle",
                    "task_id": task.id,
                    "from": from_value,
                    "to": value,
                    "triggered_sector_change": triggered_sector_change,
                    "outcome": outcome,
                },
            )

    def handle_status_change(self, task: Task, new_status: str) -> None:
        from PySide6.QtWidgets import QWidget

        parent_widget = self._main_window if isinstance(self._main_window, QWidget) else None
        try:
            completed_at = None
            if new_status == "done":
                from datetime import datetime, timezone

                completed_at = datetime.now(timezone.utc).isoformat()
            self._repo.update(task.id, status=Status(new_status), completed_at=completed_at)
        except TaskNotFoundError as exc:
            # Task sumiu durante a troca de status: abortar o refresh otimista.
            _LOG.warning(
                "status_change abortado: task %s nao encontrada: %s",
                task.id,
                exc,
                extra={"task_id": task.id},
            )
            ErrorDialog.show_io_error(parent_widget, exc, str(self._repo.db_path))
            return
        except sqlite3.Error as exc:
            _LOG.error(
                "status_change falhou para task %s: %s",
                task.id,
                exc,
                extra={"task_id": task.id, "db_path": self._repo.db_path},
            )
            ErrorDialog.show_io_error(parent_widget, exc, str(self._repo.db_path))
            return

        self._task_list.refresh(self._repo.list_active())
