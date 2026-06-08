from __future__ import annotations

import logging
import random
import sqlite3
import uuid
from datetime import datetime, timezone

from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QApplication

from task_manager_desktop.controllers._boundary import (
    coerce_flag,
    recompute_sector,
    resolve_status,
)
from task_manager_desktop.core.cycles import resolve_cycles
from task_manager_desktop.core.id_gen import generate_id
from task_manager_desktop.core.models import Sector, Subtask, Task
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.dialogs import ErrorDialog
from task_manager_desktop.ui.dialogs.new_task_dialog import NewTaskDialog
from task_manager_desktop.ui.task_list import TaskList
from task_manager_desktop.ui.toast import ToastWidget

_LOG = logging.getLogger(__name__)

# Paleta de cores das subtasks (mesma usada pelo SubtaskPane).
_SUBTASK_COLORS = ["#F97316", "#FBBF24", "#22C55E", "#06B6D4", "#38BDF8", "#A78BFA", "#FB7185"]


class CreateTaskController(QObject):
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

    def handle(self) -> None:
        from PySide6.QtWidgets import QDialog, QWidget

        parent_widget = self._main_window if isinstance(self._main_window, QWidget) else None
        dialog = NewTaskDialog(parent_widget)
        persisted = [False]

        def submit(data: dict) -> bool:
            persisted[0] = True
            return self._persist(data, parent_widget)

        dialog.submit_handler = submit
        result = dialog.exec()
        # Compatibilidade com fakes legados que retornam Accepted sem invocar submit_handler.
        if result == QDialog.DialogCode.Accepted and not persisted[0]:
            self._persist(dialog.get_data(), parent_widget)

    def _persist(self, data: dict, parent_widget) -> bool:
        # US-020 c3: retornar False mantem dialog aberto pra nova tentativa.
        all_tasks = self._repo.list_active()
        all_tasks_dict = {t.id: t for t in all_tasks}

        # Boundary validation (source.md secao 3.5): range booleano de
        # favorito/permanente e Status resolvido ANTES de qualquer escrita.
        # Valor invalido levanta ValueError aqui, sem fallback silencioso.
        favorito = coerce_flag(data.get("favorito", False), "favorito")
        permanente = coerce_flag(data.get("permanente", False), "permanente")
        em_preparacao = coerce_flag(data.get("em_preparacao", False), "em_preparacao")
        status = resolve_status(data.get("status"))

        try:
            conn = self._repo._conn
            task_id = generate_id(conn)
        except RuntimeError as exc:
            ErrorDialog.show_io_error(parent_widget, exc, str(self._repo.db_path))
            return False

        clean_deps, cycle_desc = resolve_cycles(task_id, data["deps"], all_tasks_dict)

        task = Task(
            id=task_id,
            title=data["title"],
            status=status,
            deps=clean_deps,
            created_at=datetime.now(timezone.utc).isoformat(),
            order_index=max((t.order_index for t in all_tasks), default=0) + 1,
            favorito=favorito,
            permanente=permanente,
            em_preparacao=em_preparacao,
        )

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._repo.create(task)
            for idx, text in enumerate(data.get("subtasks", []), start=1):
                # As subtasks criadas no dialog de nova task nascem com o tipo
                # default (agent); o tipo de cada uma e ajustado depois na
                # subtask pane (o card/task nao tem mais tipo proprio).
                subtask = Subtask(
                    id=f"st-{uuid.uuid4().hex[:10]}",
                    task_id=task.id,
                    text=text,
                    color=random.choice(_SUBTASK_COLORS),
                    order_index=idx,
                )
                self._repo.create_subtask(subtask)
        except sqlite3.Error as exc:
            # sqlite3.IntegrityError (constraint) e demais erros de I/O. Abortar
            # o refresh otimista: a task nao foi gravada (simetria com edit,
            # source.md secao 3.5).
            _LOG.error(
                "create.persist falhou para task %s: %s",
                task.id,
                exc,
                extra={"task_id": task.id, "db_path": self._repo.db_path},
            )
            ErrorDialog.show_io_error(parent_widget, exc, str(self._repo.db_path))
            return False
        finally:
            QApplication.restoreOverrideCursor()

        if data.get("coin_favorite"):
            self._task_list.set_coin_favorite(task.id, True)

        if cycle_desc and parent_widget:
            toast = ToastWidget(parent_widget)
            toast.show_message(
                "Ciclo de dependência detectado. Dependência mais antiga removida automaticamente."
            )

        # Recomputa o setor da task recem-criada e expoe para a UI consumir.
        self._last_persisted_task, self._last_sector = recompute_sector(self._repo, task.id)

        self._task_list.refresh(self._repo.list_active())
        return True
