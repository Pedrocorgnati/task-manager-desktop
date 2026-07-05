from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QDrag,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QPainter,
    QPixmap,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.core.filters import (
    ALL_TASK_TYPES,
    card_matches_subtasks,
    is_active,
)
from task_manager_desktop.core.models import Sector, Task, TaskType
from task_manager_desktop.core.sector import (
    PERMANENT_ACCENT,
    compute_sector,
    count_open_deps,
)
from task_manager_desktop.ui.theme import PALETTE, SPLITTER_SIZES

if TYPE_CHECKING:
    from task_manager_desktop.repositories.task_repository import TaskRepository

_log = logging.getLogger(__name__)

# Ordem canonica de renderizacao dos setores. Explicita e com Sector.PERMANENT
# por ultimo (source.md secao 3.6). `_SECTOR_ORDER` e mantido como alias para
# nao quebrar referencias internas.
RENDER_ORDER: list[Sector] = [
    Sector.ACTIVE,
    Sector.EM_PREPARACAO,
    Sector.WAITING,
    Sector.BLOCKED,
    Sector.DONE,
    Sector.PERMANENT,
]
_SECTOR_ORDER = RENDER_ORDER

_SECTOR_LABELS = {
    Sector.ACTIVE: "Em execução",
    Sector.EM_PREPARACAO: "Em preparação",
    Sector.WAITING: "Fila",
    Sector.BLOCKED: "Bloqueadas",
    Sector.DONE: "Concluídas",
    Sector.PERMANENT: "Permanentes",
}

_SECTOR_TESTIDS = {
    Sector.ACTIVE: "task-list-active-section",
    Sector.EM_PREPARACAO: "task-list-preparing-section",
    Sector.WAITING: "task-list-waiting-section",
}

_ROLE_TYPE = Qt.ItemDataRole.UserRole + 1  # "separator" | "task" | "placeholder"
_ROLE_TASK_ID = Qt.ItemDataRole.UserRole + 2  # str task id
_ROLE_SECTOR = Qt.ItemDataRole.UserRole + 3  # Sector.value int
_TYPE_ACTIVE_COLLAPSE_TOGGLE = "active-collapse-toggle"

# Setores recolhidos pelo chevron de colapso: tudo de "Fila" para baixo. "Em
# execução" e "Em preparação" permanecem sempre visiveis quando colapsado.
_COLLAPSIBLE_SECTORS = frozenset(
    {Sector.WAITING, Sector.BLOCKED, Sector.DONE, Sector.PERMANENT}
)

_SECTOR_COLORS = {
    Sector.ACTIVE: "#22C55E",
    Sector.EM_PREPARACAO: "#86EFAC",
    Sector.WAITING: "#EAB308",
    Sector.BLOCKED: "#A1A1AA",
    Sector.DONE: "#686C78",
    Sector.PERMANENT: PERMANENT_ACCENT,
}


def sort_sector_tasks(tasks: list[Task]) -> list[Task]:
    """Ordem determinista das tasks de um setor.

    Funcao pura: `(favorito DESC, order_index ASC, id ASC)` (source.md AC-13).
    Favoritos ficam no topo; o `id` como ultimo criterio garante que duas
    execucoes sobre a mesma entrada produzam exatamente a mesma ordem. O score
    de ranqueamento soma os tres marcadores persistidos (estrela + moeda +
    bolinha), cada um com peso 1.
    """
    return sorted(
        tasks,
        key=lambda t: (
            -(
                int(bool(t.favorito))
                + int(bool(getattr(t, "coin_favorite", False)))
                + int(bool(getattr(t, "dot_favorite", False)))
            ),
            not t.favorito,
            t.order_index,
            t.id,
        ),
    )


def is_cross_block_drop(reordered_favorito_flags: list[bool]) -> bool:
    """True se a ordem resultante interleava favoritos e nao-favoritos.

    Funcao pura. Dentro de um setor os favoritos formam um bloco contiguo no
    topo; um drop que coloque um nao-favorito antes de um favorito (ou vice
    versa) cruza a fronteira do bloco e e invalido (source.md AC-8). A ordem
    valida e sempre `[True...False...]`, i.e. igual a ela mesma ordenada
    decrescente.
    """
    return reordered_favorito_flags != sorted(reordered_favorito_flags, reverse=True)


def _task_sector(task: Task, all_tasks: dict[str, Task]) -> Sector:
    has_open = count_open_deps(task.deps, all_tasks) > 0
    sector, _ = compute_sector(
        task.status,
        has_open,
        task.permanente,
        getattr(task, "em_preparacao", False),
    )
    return sector


class _InnerList(QListWidget):
    """QListWidget subclass that validates and persists DnD reorder."""

    def __init__(self, outer: TaskList) -> None:
        super().__init__(outer)
        self._outer = outer
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Rolagem suave por pixel: o default ScrollPerItem saltava um card
        # inteiro por entalhe da roda (sensacao de "deslocar o bloco inteiro").
        # ScrollPerPixel + singleStep pequeno faz a lista descer suavemente,
        # fracao de card por entalhe, sem pulos bruscos.
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(22)
        self.setObjectName("taskListWidget")
        self.setProperty("testid", "task-list-widget")
        self.setSpacing(5)

    # ------------------------------------------------------------------
    # Keyboard navigation — belt-and-suspenders (window shortcuts primary)
    # ------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        key = event.key()
        if key == Qt.Key.Key_Up:
            self._outer.select_prev()
            event.accept()
        elif key == Qt.Key.Key_Down:
            self._outer.select_next()
            event.accept()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            task = self._outer.get_selected_task()
            if task is not None:
                self._outer.enter_pressed_on_selection.emit(task)
            event.accept()
        else:
            super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _type_at(self, row: int) -> str:
        item = self.item(row)
        return item.data(_ROLE_TYPE) if item else ""

    def _sector_at(self, row: int) -> int:
        item = self.item(row)
        return item.data(_ROLE_SECTOR) if item else 0

    def _task_id_at(self, row: int) -> str:
        item = self.item(row)
        return item.data(_ROLE_TASK_ID) if item else ""

    def _task_favorito(self, task_id: str) -> bool:
        """Flag favorito da task pelo id, consultando o cache do outer widget."""
        for task in self._outer._tasks:
            if task.id == task_id:
                return bool(task.favorito)
        return False

    def _sector_for_row(self, row: int) -> int:
        """Walk backwards to find the separator enclosing this row."""
        for r in range(row, -1, -1):
            if self._type_at(r) == "separator":
                return self._sector_at(r)
        return 0

    def _task_rows_in_sector(self, sector_value: int) -> list[int]:
        return [
            r
            for r in range(self.count())
            if self._type_at(r) == "task" and self._sector_for_row(r) == sector_value
        ]

    # ------------------------------------------------------------------
    # Drag-and-drop
    # ------------------------------------------------------------------

    def startDrag(self, supported_actions: Qt.DropAction) -> None:
        item = self.currentItem()
        if item is None or item.data(_ROLE_TYPE) != "task":
            super().startDrag(supported_actions)
            return
        widget = self.itemWidget(item)
        if widget is None:
            super().startDrag(supported_actions)
            return

        src = widget.grab()
        ghost = QPixmap(src.size())
        ghost.fill(Qt.GlobalColor.transparent)
        painter = QPainter(ghost)
        painter.setOpacity(0.6)
        painter.drawPixmap(0, 0, src)
        painter.end()

        drag = QDrag(self)
        mime = self.model().mimeData(self.selectedIndexes())
        drag.setMimeData(mime)
        drag.setPixmap(ghost)
        drag.setHotSpot(ghost.rect().center())
        drag.exec(supported_actions)

    # Aceita o drag interno em qualquer ponto do viewport. Sem isto, o
    # Qt rejeita posicoes "vazias" (gap entre cards, area abaixo do ultimo
    # card) e o dropEvent nunca chega a ser entregue.
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        super().dragEnterEvent(event)
        if event.source() is self:
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        super().dragMoveEvent(event)
        if event.source() is self:
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        source_row = self.currentRow()
        if self._type_at(source_row) != "task":
            event.ignore()
            return

        source_sector = self._sector_for_row(source_row)
        source_id = self._task_id_at(source_row)

        # Setor Concluidas e imutavel.
        if source_sector == Sector.DONE.value:
            event.ignore()
            return

        # O drop sempre resolve para um card, mesmo caindo no gap entre
        # cards ou abaixo do ultimo: o card arrastado e inserido acima do
        # card que estava abaixo do ponto de drop.
        drop_y = event.position().toPoint().y()

        # Drop cross-setor continua no-op silencioso (setor deriva do status).
        nearest_row = self._nearest_task_row(drop_y)
        if nearest_row < 0 or self._sector_for_row(nearest_row) != source_sector:
            event.ignore()
            return

        orig_ids = [self._task_id_at(r) for r in self._task_rows_in_sector(source_sector)]
        ordered_ids = self._reordered_sector_ids(source_sector, source_id, drop_y)

        # Drop invalido: dentro de um setor favoritos formam um bloco contiguo
        # no topo. Mover um card para dentro do outro bloco quebra a ordenacao
        # determinista (favorito DESC) e e rejeitado (source.md AC-8).
        fav_flags = [self._task_favorito(tid) for tid in ordered_ids]
        if is_cross_block_drop(fav_flags):
            # Bloco = lado favorito/nao-favorito da fronteira que o DnD nao pode
            # cruzar. `from_block` deriva do card arrastado; `to_block` e o bloco
            # oposto, alvo do drop rejeitado (source.md secao 1.6 e secao 9).
            from_block = "favorito" if self._task_favorito(source_id) else "nao-favorito"
            to_block = "nao-favorito" if from_block == "favorito" else "favorito"
            # Evento estruturado (source.md secao 9): payload key-value consistente
            # com os demais eventos de observabilidade, em vez de string crua. Os
            # tres campos exigidos (task_id, from_block, to_block) vao tanto no
            # `extra=` (consumo por handlers estruturados) quanto interpolados na
            # mensagem (legibilidade em handlers de texto puro). Debug, sem toast.
            _log.debug(
                "dnd.drop_rejected event=dnd.drop_rejected reason=cross-block "
                "task_id=%s from_block=%s to_block=%s",
                source_id,
                from_block,
                to_block,
                extra={
                    "event": "dnd.drop_rejected",
                    "reason": "cross-block",
                    "task_id": source_id,
                    "from_block": from_block,
                    "to_block": to_block,
                },
            )
            event.ignore()
            return

        event.acceptProposedAction()

        if ordered_ids == orig_ids:
            return  # ordem inalterada: aceita o gesto sem persistir

        new_pairs = [(tid, idx + 1) for idx, tid in enumerate(ordered_ids)]

        repo = self._outer._repo
        if repo is None:
            return

        try:
            repo.update_order_indexes(new_pairs)
        except sqlite3.OperationalError as exc:
            # Reverte recarregando a lista do estado anterior em cache.
            self._outer.refresh(self._outer._tasks)
            parent_win = self._outer._main_window
            parent_w = parent_win if isinstance(parent_win, QWidget) else None
            from task_manager_desktop.ui.dialogs import ErrorDialog

            ErrorDialog.show_io_error(parent_w, exc, repo.db_path)
            return

        # Re-renderiza a partir do repo: order_index dita a ordem visual.
        self._outer.refresh(repo.list_active())
        self._select_task_row(source_id)

        parent_win = self._outer._main_window
        if isinstance(parent_win, QWidget):
            from task_manager_desktop.ui.toast import ToastWidget

            toast = ToastWidget(parent_win)
            toast.show_info("Ordem atualizada.")

    def _nearest_task_row(self, y: int) -> int:
        """Row do item 'task' cuja faixa vertical esta mais proxima de y.
        Retorna -1 se nao houver tasks. Garante que o drop sempre resolve
        para um card, mesmo caindo no gap entre eles."""
        best_row = -1
        best_dist: int | None = None
        for r in range(self.count()):
            if self._type_at(r) != "task":
                continue
            rect = self.visualItemRect(self.item(r))
            if rect.top() <= y <= rect.bottom():
                return r
            dist = rect.top() - y if y < rect.top() else y - rect.bottom()
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_row = r
        return best_row

    def _reordered_sector_ids(
        self, sector_value: int, source_id: str, drop_y: int
    ) -> list[str]:
        """Nova ordem de task ids do setor apos soltar source_id em drop_y.
        O card cai acima do primeiro card cujo centro esta abaixo de drop_y;
        se drop_y estiver abaixo de todos, vai para o fim do setor."""
        rows = self._task_rows_in_sector(sector_value)
        ids = [self._task_id_at(r) for r in rows]
        if source_id in ids:
            ids.remove(source_id)

        insert_at = len(ids)
        for r in rows:
            tid = self._task_id_at(r)
            if tid == source_id:
                continue
            center_y = self.visualItemRect(self.item(r)).center().y()
            if drop_y < center_y:
                insert_at = ids.index(tid)
                break

        ids.insert(insert_at, source_id)
        return ids

    def _select_task_row(self, task_id: str) -> None:
        for r in range(self.count()):
            if self._type_at(r) == "task" and self._task_id_at(r) == task_id:
                self.setCurrentRow(r)
                return


class TaskList(QWidget):
    task_selected = Signal(object)
    enter_pressed_on_selection = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("testid", "task-list-container")
        self.setFixedWidth(int(SPLITTER_SIZES[0]))
        self._callbacks: dict[str, Any] = {}
        self._tasks: list[Task] = []
        self._cards: list[Any] = []
        self._repo: TaskRepository | None = None
        self._main_window: QWidget | None = None
        self._task_types: frozenset[str] = ALL_TASK_TYPES
        self._active_only_collapsed = False
        self._search_text = ""
        # Overlay ancorado no canto inferior direito (ver attach_test_mode_grid).
        self._test_mode_grid: QWidget | None = None

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._header_host = QWidget(self)
        self._header_host.setObjectName("taskListHeaderHost")
        self._header_host.setProperty("testid", "task-list-header-host")
        # Layout vertical: primeira linha com os itens existentes do header
        # (set_header_widget), segunda linha com o input de busca.
        header_outer = QVBoxLayout(self._header_host)
        header_outer.setContentsMargins(10, 6, 10, 6)
        header_outer.setSpacing(6)

        self._header_layout = QHBoxLayout()
        self._header_layout.setContentsMargins(0, 0, 0, 0)
        self._header_layout.setSpacing(0)
        header_outer.addLayout(self._header_layout)

        # Linha de baixo: input de busca que filtra os cards por texto (titulo
        # ou id da task). Vive dentro do task-list-header-host.
        self._search_input = QLineEdit(self._header_host)
        self._search_input.setObjectName("taskSearchInput")
        self._search_input.setProperty("testid", "task-list-search-input")
        self._search_input.setPlaceholderText("Buscar tasks...")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(self._on_search_text_changed)
        header_outer.addWidget(self._search_input)

        self._layout.addWidget(self._header_host)

        self._empty_label = QLabel(
            "Sem tasks. Clique em + para criar a primeira.", self
        )
        self._empty_label.setObjectName("emptyStateText")
        self._empty_label.setProperty("testid", "task-list-empty-state")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._empty_label.hide()
        self._layout.addWidget(self._empty_label)

        self._empty_filter_label = QLabel(
            "Nenhuma task corresponde a este filtro.", self
        )
        self._empty_filter_label.setObjectName("filterEmptyStateText")
        self._empty_filter_label.setProperty("testid", "task-list-filter-empty-state")
        self._empty_filter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_filter_label.setWordWrap(True)
        self._empty_filter_label.hide()
        self._layout.addWidget(self._empty_filter_label)

        self._inner = _InnerList(self)
        self._inner.itemSelectionChanged.connect(self._update_selection_glow)
        self._layout.addWidget(self._inner)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_callbacks(self, callbacks: dict[str, Any]) -> None:
        self._callbacks = callbacks

    def set_repo(self, repo: TaskRepository) -> None:
        self._repo = repo

    def set_main_window(self, main_window: QWidget) -> None:
        self._main_window = main_window

    def set_header_widget(self, widget: QWidget) -> None:
        while self._header_layout.count():
            item = self._header_layout.takeAt(0)
            old = item.widget()
            if old is not None and old is not widget:
                # setParent(None) apenas desancora; o widget orfao continuaria
                # vivo com suas conexoes de sinal. deleteLater() agenda a
                # destruicao real e libera essas conexoes (Qt resource leak).
                old.setParent(None)
                old.deleteLater()
        widget.setParent(self._header_host)
        self._header_layout.addWidget(widget)

    def attach_test_mode_grid(self, widget: QWidget) -> None:
        """Ancora a grid de test-mode como overlay flutuante no canto
        inferior direito desta coluna (coluna 1 / task-list-pane)."""
        self._test_mode_grid = widget
        widget.setParent(self)
        widget.show()
        widget.raise_()
        self._reposition_test_mode_grid()

    _TEST_MODE_GRID_MARGIN = 8

    def _reposition_test_mode_grid(self) -> None:
        grid = self._test_mode_grid
        if grid is None:
            return
        grid.adjustSize()
        margin = self._TEST_MODE_GRID_MARGIN
        x = self.width() - grid.width() - margin
        y = self.height() - grid.height() - margin
        grid.move(max(0, x), max(0, y))
        grid.raise_()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._reposition_test_mode_grid()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self, tasks: list[Task] | None = None, pulse_task_id: str | None = None) -> None:
        """Rebuild the list.

        If tasks is provided, update the cached list and rebuild.
        If tasks is None, reload from repo (if available) or rebuild from cache.
        pulse_task_id: if set, the matching card will play a brief pulse animation after rebuild.
        """
        if tasks is not None:
            self._tasks = tasks
        elif self._repo is not None:
            self._tasks = self._repo.list_active()
        self._rebuild(self._tasks)
        if pulse_task_id:
            self._pulse_card(pulse_task_id)

    def _pulse_card(self, task_id: str) -> None:
        from task_manager_desktop.ui.task_card import TaskCard

        for card in self._cards:
            if isinstance(card, TaskCard) and card._task.id == task_id:
                card.pulse()
                break

    def sync_task_notes(self, task_id: str, notes: str) -> None:
        """Reconcilia o cache em memoria apos um save de notas do reader.

        O painel Markdown persiste as notas direto no banco, mas os objetos
        Task vivem em cache aqui (self._tasks) e dentro de cada TaskCard. Sem
        esta reconciliacao, re-selecionar o mesmo card re-emite o Task antigo
        e o editor recarrega o texto pre-edicao — efeito "perdi tudo que escrevi".
        """
        import dataclasses

        from task_manager_desktop.ui.task_card import TaskCard

        for idx, task in enumerate(self._tasks):
            if task.id == task_id:
                self._tasks[idx] = dataclasses.replace(task, notes=notes)
                break
        for card in self._cards:
            if isinstance(card, TaskCard) and card._task.id == task_id:
                card._task = dataclasses.replace(card._task, notes=notes)
                break

    def _on_search_text_changed(self, text: str) -> None:
        self._search_text = text.strip().casefold()
        self._rebuild(self._tasks)

    def _matches_search(self, task: Task) -> bool:
        if not self._search_text:
            return True
        haystack = f"{task.title} {task.id}".casefold()
        return self._search_text in haystack

    def _update_selection_glow(self) -> None:
        """Aplica o halo branco no card atualmente selecionado e o remove dos
        demais, para sinalizar visualmente qual task esta selecionada."""
        from task_manager_desktop.ui.task_card import TaskCard

        selected = self.get_selected_task()
        selected_id = selected.id if selected is not None else None
        for card in self._cards:
            if isinstance(card, TaskCard):
                card.set_selected(card._task.id == selected_id)

    def set_filters(
        self,
        task_types: Iterable[str | TaskType] | None = None,
    ) -> None:
        self._task_types = (
            ALL_TASK_TYPES
            if task_types is None
            else frozenset(t.value if isinstance(t, TaskType) else str(t) for t in task_types)
        )
        self._rebuild(self._tasks)

    def apply_filter(
        self,
        task_types: Iterable[str | TaskType] | None = None,
    ) -> None:
        self.set_filters(task_types=task_types)

    def has_selection(self) -> bool:
        return self.get_selected_task() is not None

    def selected_task(self) -> Task | None:
        return self.get_selected_task()

    def clear_selection(self) -> None:
        self._inner.clearSelection()
        self._inner.setCurrentRow(-1)

    def visible_task_ids(self) -> list[str]:
        return [
            self._inner._task_id_at(r)
            for r in range(self._inner.count())
            if self._inner._type_at(r) == "task"
        ]

    def _task_rows(self) -> list[int]:
        return [
            r
            for r in range(self._inner.count())
            if self._inner._type_at(r) == "task"
        ]

    def get_selected_task(self) -> Task | None:
        row = self._inner.currentRow()
        if row < 0:
            return None
        if self._inner._type_at(row) != "task":
            return None
        tid = self._inner._task_id_at(row)
        if not tid:
            return None
        for task in self._tasks:
            if task.id == tid:
                return task
        return None

    def select_next(self) -> None:
        rows = self._task_rows()
        if not rows:
            return
        cur = self._inner.currentRow()
        next_row = next((r for r in rows if r > cur), None)
        if next_row is None:
            next_row = rows[-1]
        self._inner.setCurrentRow(next_row)

    def select_prev(self) -> None:
        rows = self._task_rows()
        if not rows:
            return
        cur = self._inner.currentRow()
        prev_row = next((r for r in reversed(rows) if r < cur), None)
        if prev_row is None:
            prev_row = rows[0]
        self._inner.setCurrentRow(prev_row)

    def open_selected(self) -> None:
        task = self.get_selected_task()
        if task is not None:
            self.task_selected.emit(task)

    def move_card_to_sector(self, task_id: str, sector: int) -> None:
        """Move a card to a new sector (incremental render).

        Reloads tasks from repo to get fresh sector assignments for all tasks,
        then rebuilds. No-op if task_id is not found.
        For TASK-3, this will be replaced with a true incremental implementation.
        """
        if self._repo is not None:
            self.refresh(self._repo.list_active())
        else:
            self.refresh()

    # ------------------------------------------------------------------
    # Internal rebuild
    # ------------------------------------------------------------------

    def _subtask_types_by_task(self) -> dict[str, set[str]]:
        """Mapa task_id -> tipos das subtasks, lido do repo (uma query).

        Sem repo (ex.: cards montados a partir de cache em testes) retorna {}.
        Falha de I/O nunca derruba a render: o filtro trata o card como "sem
        subtasks" (some sob filtro ativo), e o erro e logado.
        """
        if self._repo is None:
            return {}
        try:
            return self._repo.subtask_types_by_task()
        except Exception:
            _log.exception("task_list.subtask_types_lookup_failed")
            return {}

    def _rebuild(self, tasks: list[Task]) -> None:
        self._inner.clear()
        self._cards = []
        all_tasks: dict[str, Task] = {t.id: t for t in tasks}

        # Regra de visibilidade do card principal (o tipo migrou para as
        # subtasks): com os 3 checkboxes marcados (filtro inativo) renderizam
        # TODOS os cards, inclusive os sem subtasks. Ao desmarcar qualquer
        # tipo, o filtro passa a valer e so renderizam os cards que possuem ao
        # menos uma subtask de um tipo selecionado.
        filter_active = is_active(task_types=self._task_types)
        if filter_active:
            sub_types = self._subtask_types_by_task()
            visible_tasks = [
                t
                for t in tasks
                if card_matches_subtasks(
                    sub_types.get(t.id, ()), task_types=self._task_types
                )
            ]
        else:
            visible_tasks = list(tasks)

        # Filtro de busca textual (input do header): aplicado sobre o resultado
        # do filtro de tipo. Casa por titulo ou id da task.
        search_active = bool(self._search_text)
        if search_active:
            visible_tasks = [t for t in visible_tasks if self._matches_search(t)]

        # CL-030: banco vazio exibe 4 headers + placeholder; empty_label so para "sem resultados de filtro"
        filter_no_match = (filter_active or search_active) and not visible_tasks

        self._empty_label.setVisible(False)
        self._empty_filter_label.setVisible(filter_no_match)
        self._inner.setVisible(not filter_no_match)

        if filter_no_match:
            return

        groups: dict[Sector, list[Task]] = {s: [] for s in _SECTOR_ORDER}
        for task in visible_tasks:
            groups[_task_sector(task, all_tasks)].append(task)
        # Ordem determinista por setor: favorito DESC, order_index ASC, id ASC.
        for sector_key in groups:
            groups[sector_key] = sort_sector_tasks(groups[sector_key])

        # O chevron de colapso vive logo abaixo da ultima categoria sempre-visivel
        # presente: "Em preparação" quando ha tasks nela, senao "Em execução".
        # Assim o colapso recolhe apenas de "Fila" para baixo.
        collapse_anchor = (
            Sector.EM_PREPARACAO if groups[Sector.EM_PREPARACAO] else Sector.ACTIVE
        )

        for sector in _SECTOR_ORDER:
            sector_tasks = groups[sector]
            if self._active_only_collapsed and sector in _COLLAPSIBLE_SECTORS:
                continue
            if (filter_active or search_active) and not sector_tasks:
                continue
            # O setor Permanentes nao e um setor-base sempre visivel: so
            # aparece quando ha tasks permanentes concluidas. Um header
            # "Permanentes" vazio seria ruido (source.md secao 3.6).
            if sector == Sector.PERMANENT and not sector_tasks:
                continue
            # "Em preparação" e um setor opt-in: so aparece quando ha alguma
            # task marcada manualmente; um header vazio seria ruido.
            if sector == Sector.EM_PREPARACAO and not sector_tasks:
                continue
            self._add_separator(sector)
            if not sector_tasks:
                self._add_placeholder(sector)
            else:
                for task in sector_tasks:
                    self._add_task_item(task, tasks, all_tasks, sector)
            if sector == collapse_anchor and sector_tasks:
                self._add_active_collapse_toggle(collapse_anchor)

        # Reaplica o halo branco apos reconstruir os cards (clear() perdeu o
        # estado visual; a selecao do QListWidget pode persistir).
        self._update_selection_glow()

    def _add_separator(self, sector: Sector) -> None:
        item = QListWidgetItem(_SECTOR_LABELS[sector])
        item.setData(_ROLE_TYPE, "separator")
        item.setData(_ROLE_SECTOR, sector.value)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setSizeHint(QSize(1, 34))
        self._inner.addItem(item)

        row = QWidget(self._inner)
        row.setObjectName("sectorHeaderRow")
        testid = _SECTOR_TESTIDS.get(sector)
        if testid is not None:
            row.setProperty("testid", testid)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(6, 6, 6, 3)
        layout.setSpacing(10)

        title = QLabel(_SECTOR_LABELS[sector].upper(), row)
        title.setObjectName("sectorTitle")
        title.setMinimumWidth(140)
        title.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        title.setStyleSheet(f"color: {_SECTOR_COLORS[sector]};")
        layout.addWidget(title)

        rule = QFrame(row)
        rule.setObjectName("sectorRule")
        rule.setFrameShape(QFrame.Shape.HLine)
        rule.setStyleSheet(f"background: {_SECTOR_COLORS[sector]}; border: none;")
        layout.addWidget(rule, 1)

        self._inner.setItemWidget(item, row)

    def _add_active_collapse_toggle(self, sector: Sector = Sector.ACTIVE) -> None:
        item = QListWidgetItem()
        item.setData(_ROLE_TYPE, _TYPE_ACTIVE_COLLAPSE_TOGGLE)
        item.setData(_ROLE_SECTOR, sector.value)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setSizeHint(QSize(1, 28))
        self._inner.addItem(item)

        row = QWidget(self._inner)
        row.setObjectName("activeCollapseRow")
        row.setProperty("testid", "active-collapse-row")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(6, 0, 6, 3)
        layout.setSpacing(0)

        button = QToolButton(row)
        button.setObjectName("activeCollapseButton")
        button.setProperty("testid", "active-collapse-button")
        button.setText("⌃" if self._active_only_collapsed else "⌄")
        button.setAccessibleName(
            "Mostrar todos os setores"
            if self._active_only_collapsed
            else "Recolher Fila e setores abaixo"
        )
        button.setToolTip(
            "Mostrar todos os setores"
            if self._active_only_collapsed
            else "Recolher Fila e setores abaixo"
        )
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(self._toggle_active_only_collapsed)

        layout.addStretch(1)
        layout.addWidget(button)
        layout.addStretch(1)
        self._inner.setItemWidget(item, row)

    def _toggle_active_only_collapsed(self) -> None:
        self._active_only_collapsed = not self._active_only_collapsed
        self._rebuild(self._tasks)

    def _add_placeholder(self, sector: Sector) -> None:
        item = QListWidgetItem("vazio")
        item.setData(_ROLE_TYPE, "placeholder")
        item.setData(_ROLE_SECTOR, sector.value)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setSizeHint(QSize(1, 22))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setForeground(QColor(PALETTE["TEXT_MUTED"]))
        self._inner.addItem(item)

    def _add_task_item(
        self,
        task: Task,
        all_tasks_list: list[Task],
        all_tasks_dict: dict[str, Task],
        sector: Sector,
    ) -> None:
        from task_manager_desktop.ui.task_card import TaskCard

        item = QListWidgetItem()
        item.setData(_ROLE_TYPE, "task")
        item.setData(_ROLE_TASK_ID, task.id)
        item.setData(_ROLE_SECTOR, sector.value)
        item.setFlags(
            Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsDragEnabled
            | Qt.ItemFlag.ItemIsDropEnabled
        )
        self._inner.addItem(item)

        card = TaskCard(task, self._callbacks, all_tasks_list, self._inner)
        card.selected.connect(self.task_selected.emit)
        if task.permanente and self._repo is not None:
            try:
                due_at = self._repo.get_permanent_schedule(task.id)
                if due_at:
                    card.set_schedule_active(due_at)
            except Exception:
                pass
        # Mantem a altura do item alinhada ao card real para evitar "gaps"
        # visuais grandes entre cards. O espacamento entre itens fica sob
        # controle exclusivo do QListWidget.setSpacing(5).
        item.setSizeHint(QSize(1, card.sizeHint().height()))
        self._inner.setItemWidget(item, card)
        self._cards.append(card)
