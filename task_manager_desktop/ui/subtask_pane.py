from __future__ import annotations

import random
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QSize, Qt
from PySide6.QtGui import QDropEvent, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.core.models import Subtask, Task
from task_manager_desktop.ui.icons import BROOM_SVG, svg_to_icon

if TYPE_CHECKING:
    from task_manager_desktop.repositories.task_repository import TaskRepository

_ROLE_SUBTASK_ID = Qt.ItemDataRole.UserRole + 1
_ROLE_TEXT = Qt.ItemDataRole.UserRole + 2
_EXPANDED_MARGINS = (8, 10, 8, 10)
_COLLAPSED_MARGINS = (2, 10, 2, 10)
_EXPANDED_WIDTH = 210
_SUBTASK_CHECKBOX_WIDTH = 20
# Gap entre o checkbox e o card: metade do valor anterior (7 -> 4, ~7/2 arredondado).
_SUBTASK_ROW_SPACING = 4
_SUBTASK_CARD_WIDTH = int(
    (
        _EXPANDED_WIDTH
        - _EXPANDED_MARGINS[0]
        - _EXPANDED_MARGINS[2]
        - _SUBTASK_CHECKBOX_WIDTH
        - _SUBTASK_ROW_SPACING
    )
    * 0.92
)

_COLORS = [
    "#F97316",
    "#FBBF24",
    "#22C55E",
    "#06B6D4",
    "#38BDF8",
    "#A78BFA",
    "#FB7185",
]


class _SubtaskRow(QWidget):
    def __init__(
        self,
        subtask: Subtask,
        on_notes_changed: Callable[[Subtask, str], None],
        on_expanded_changed: Callable[[bool], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._subtask = subtask
        self._on_notes_changed = on_notes_changed
        self._on_expanded_changed = on_expanded_changed
        self._expanded = False
        self._compact = False
        self._hovered = False
        self.setObjectName("subtaskRow")
        self.setProperty("testid", f"subtask-row-{subtask.id}")
        self.setProperty("state", subtask.state)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

        self.checkbox = QCheckBox(self)
        self.checkbox.setObjectName("subtaskCheckbox")
        self.checkbox.setProperty("testid", f"subtask-checkbox-{subtask.id}")
        self.checkbox.setTristate(True)
        self.checkbox.setCheckState(self._qt_state(subtask.state))
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkbox.setFixedWidth(_SUBTASK_CHECKBOX_WIDTH)

        self._card = QWidget(self)
        self._card.setObjectName("subtaskCard")
        self._card.setProperty("testid", f"subtask-card-{subtask.id}")
        self._card.setProperty("state", subtask.state)
        self._card.setFixedWidth(_SUBTASK_CARD_WIDTH)
        self._card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.label = QLabel(subtask.text, self)
        self.label.setObjectName("subtaskText")
        self.label.setProperty("testid", f"subtask-text-{subtask.id}")
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        self.label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.label.setProperty("color", subtask.color)
        self.label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.label.mouseDoubleClickEvent = lambda _event: self._begin_inline_edit()

        self._inline_edit = QLineEdit(self)
        self._inline_edit.setObjectName("subtaskInlineEdit")
        self._inline_edit.setProperty("testid", f"subtask-inline-edit-{subtask.id}")
        self._inline_edit.setText(subtask.text)
        self._inline_edit.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self._inline_edit.hide()
        self._inline_edit.editingFinished.connect(self._commit_inline_edit)
        self._inline_edit.returnPressed.connect(self._commit_inline_edit)

        self.notes_toggle = QToolButton(self)
        self.notes_toggle.setObjectName("subtaskNotesToggle")
        self.notes_toggle.setProperty("testid", f"subtask-notes-toggle-{subtask.id}")
        self.notes_toggle.setAccessibleName("Abrir notas da subtask")
        self.notes_toggle.setFixedSize(20, 20)
        self.notes_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        # Reserva o slot do chevron no layout: mostrar/ocultar no hover apenas
        # alterna a visibilidade, sem refluir o texto (sem efeito de "deslizar").
        _toggle_policy = self.notes_toggle.sizePolicy()
        _toggle_policy.setRetainSizeWhenHidden(True)
        self.notes_toggle.setSizePolicy(_toggle_policy)

        self.notes_editor = QPlainTextEdit(self)
        self.notes_editor.setObjectName("subtaskNotesEditor")
        self.notes_editor.setProperty("testid", f"subtask-notes-editor-{subtask.id}")
        self.notes_editor.setPlaceholderText("Notas da subtask...")
        self.notes_editor.setPlainText(subtask.notes)
        self.notes_editor.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.notes_editor.setFixedHeight(70)
        self.notes_editor.hide()

        card_layout = QHBoxLayout(self._card)
        card_layout.setContentsMargins(8, 4, 8, 4)
        card_layout.setSpacing(6)
        card_layout.addWidget(self.label, 1)
        card_layout.addWidget(self._inline_edit, 1)
        card_layout.addWidget(self.notes_toggle, 0, Qt.AlignmentFlag.AlignVCenter)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(_SUBTASK_ROW_SPACING)
        top_row.addWidget(self.checkbox, 0, Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(self._card, 0, Qt.AlignmentFlag.AlignVCenter)
        top_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(5)
        layout.addLayout(top_row)
        layout.addWidget(self.notes_editor)

        self.notes_toggle.clicked.connect(self.toggle_notes)
        self.notes_editor.textChanged.connect(self._autosave_notes)
        self.apply_state(subtask.state)
        self._sync_notes_toggle()

    def set_compact(self, compact: bool) -> None:
        self._compact = compact
        self.checkbox.setVisible(not compact)
        self.label.setVisible(not compact and self._inline_edit.isHidden())
        self._inline_edit.setVisible(False)
        if compact:
            self._card.setFixedWidth(24)
        else:
            self._card.setFixedWidth(_SUBTASK_CARD_WIDTH)
        self._sync_notes_toggle()

    def apply_state(self, state: int) -> None:
        self._subtask.state = state
        self._subtask.done = state == 2
        self.setProperty("state", state)
        self._card.setProperty("state", state)
        self.style().unpolish(self)
        self.style().polish(self)
        self._card.style().unpolish(self._card)
        self._card.style().polish(self._card)
        font = QFont(self.label.font())
        font.setStrikeOut(state == 2)
        self.label.setFont(font)
        base_color = self._subtask.color
        if state == 1:
            card_bg, text_color = "#22C55E", "#052E16"
        else:
            card_bg, text_color = base_color, "#111116"
        # A parte colorida ocupa o card inteiro (esta div); o chevron de notas,
        # filho do card_layout, passa a ficar dentro dessa area colorida.
        self._card.setStyleSheet(
            f"QWidget#subtaskCard {{ background: {card_bg};"
            " border: none; border-radius: 8px; }"
        )
        self.label.setStyleSheet(f"color: {text_color}; background: transparent;")

    def toggle_notes(self) -> None:
        self._expanded = not self._expanded
        self.notes_editor.setVisible(self._expanded)
        self.notes_toggle.setAccessibleName(
            "Fechar notas da subtask" if self._expanded else "Abrir notas da subtask"
        )
        self._sync_notes_toggle()
        self._on_expanded_changed(self._expanded)
        if self._expanded:
            self.notes_editor.setFocus(Qt.FocusReason.MouseFocusReason)

    def _autosave_notes(self) -> None:
        notes = self.notes_editor.toPlainText()
        if notes == self._subtask.notes:
            return
        self._subtask.notes = notes
        self._on_notes_changed(self._subtask, notes)
        self._sync_notes_toggle()

    def _has_notes(self) -> bool:
        return bool(self._subtask.notes.strip())

    def _sync_notes_toggle(self) -> None:
        has_notes = self._has_notes()
        if self._compact:
            self.notes_toggle.setVisible(True)
        else:
            self.notes_toggle.setVisible(self._expanded or self._hovered or has_notes)
        self.notes_toggle.setText("⌃" if self._expanded else "⌄")
        self.notes_toggle.setProperty("hasNotes", has_notes)
        if has_notes:
            self.notes_toggle.setStyleSheet(
                "QToolButton#subtaskNotesToggle {"
                "background: rgba(5,6,8,0.25); color: #111116;"
                "border: none; border-radius: 6px; font-size: 15px; font-weight: 900; padding: 0;"
                "}"
            )
        else:
            self.notes_toggle.setStyleSheet(
                "QToolButton#subtaskNotesToggle {"
                "background: transparent; color: #111116;"
                "border: none; border-radius: 6px; font-size: 13px; font-weight: 700; padding: 0;"
                "}"
                "QToolButton#subtaskNotesToggle:hover {"
                "color: #111116;"
                "}"
            )

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._hovered = True
        self._sync_notes_toggle()
        if event is not None:
            super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._hovered = False
        self._sync_notes_toggle()
        if event is not None:
            super().leaveEvent(event)

    @staticmethod
    def _qt_state(state: int) -> Qt.CheckState:
        if state == 1:
            return Qt.CheckState.PartiallyChecked
        if state == 2:
            return Qt.CheckState.Checked
        return Qt.CheckState.Unchecked

    def _begin_inline_edit(self) -> None:
        if self._compact:
            return
        self._inline_edit.setText(self._subtask.text)
        self.label.hide()
        self._inline_edit.show()
        self._inline_edit.setFocus(Qt.FocusReason.MouseFocusReason)
        self._inline_edit.selectAll()

    def _commit_inline_edit(self) -> None:
        if self._inline_edit.isHidden():
            return
        new_text = self._inline_edit.text().strip()
        if new_text:
            self._subtask.text = new_text
            self.label.setText(new_text)
        self._inline_edit.hide()
        self.label.show()
        parent = self.parent()
        while parent is not None:
            pane = getattr(parent, "_pane", None)
            if isinstance(pane, SubtaskPane):
                pane._save_subtask_text(self._subtask)
                break
            if isinstance(parent, SubtaskPane):
                parent._save_subtask_text(self._subtask)
                break
            parent = parent.parent()


class _SubtaskList(QListWidget):
    def __init__(self, pane: SubtaskPane) -> None:
        super().__init__(pane)
        self._pane = pane
        self.setObjectName("subtaskList")
        self.setProperty("testid", "subtask-list")
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Gap entre cards: metade do valor anterior (2 -> 1).
        self.setSpacing(1)
        self._animations: list[QPropertyAnimation] = []

    def dropEvent(self, event: QDropEvent) -> None:
        before = self._capture_item_positions()
        source_row = self.currentRow()
        pos = event.position().toPoint()
        target_item = self.itemAt(pos)
        target_row = self.row(target_item) if target_item is not None else -1

        if (
            event.source() is self
            and source_row >= 0
            and target_row >= 0
            and source_row != target_row
            and self.dropIndicatorPosition() == QAbstractItemView.DropIndicatorPosition.OnItem
        ):
            item = self.takeItem(source_row)
            if source_row < target_row:
                target_row -= 1
            self.insertItem(target_row, item)
            self.setCurrentRow(target_row)
            event.accept()
        else:
            super().dropEvent(event)

        self._animate_reorder(before)
        self._pane.persist_order()

    def _capture_item_positions(self) -> dict[str, QPoint]:
        positions: dict[str, QPoint] = {}
        for row in range(self.count()):
            item = self.item(row)
            widget = self.itemWidget(item)
            subtask_id = str(item.data(_ROLE_SUBTASK_ID))
            if widget is not None:
                positions[subtask_id] = widget.pos()
        return positions

    def _animate_reorder(self, before: dict[str, QPoint]) -> None:
        self._animations.clear()
        for row in range(self.count()):
            item = self.item(row)
            widget = self.itemWidget(item)
            if widget is None:
                continue
            subtask_id = str(item.data(_ROLE_SUBTASK_ID))
            old_pos = before.get(subtask_id)
            if old_pos is None:
                continue
            new_pos = widget.pos()
            if old_pos == new_pos:
                continue
            widget.move(old_pos)
            anim = QPropertyAnimation(widget, b"pos", self)
            anim.setDuration(140)
            anim.setStartValue(old_pos)
            anim.setEndValue(new_pos)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()
            self._animations.append(anim)


class SubtaskPane(QWidget):
    """Painel central de subtasks vinculadas ao id da task selecionada."""

    def __init__(self, repo: TaskRepository | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._task: Task | None = None
        self._collapsed = False
        self.setObjectName("subtaskPane")
        self.setAccessibleName("Painel de subtasks")
        self.setProperty("testid", "subtask-pane")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(_EXPANDED_WIDTH)

        self.btn_toggle = QPushButton("[<]", self)
        self.btn_toggle.setObjectName("middleColumnToggle")
        self.btn_toggle.setAccessibleName("Colapsar painel de subtasks")
        self.btn_toggle.setFixedHeight(30)

        self.btn_add = QPushButton("+", self)
        self.btn_add.setObjectName("subtaskAddButton")
        self.btn_add.setAccessibleName("Adicionar subtask")
        self.btn_add.setFixedSize(30, 30)
        self.btn_add.setEnabled(False)

        self.btn_clear_done = QToolButton(self)
        self.btn_clear_done.setObjectName("subtaskClearDoneButton")
        self.btn_clear_done.setProperty("testid", "subtask-clear-done-button")
        self.btn_clear_done.setAccessibleName("Limpar subtasks concluídas")
        self.btn_clear_done.setToolTip("Nenhuma subtask concluída neste grupo")
        self.btn_clear_done.setIcon(svg_to_icon(BROOM_SVG, 16))
        self.btn_clear_done.setIconSize(QSize(16, 16))
        self.btn_clear_done.setFixedSize(30, 30)
        self.btn_clear_done.setEnabled(False)
        self.btn_clear_done.setCursor(Qt.CursorShape.PointingHandCursor)

        self._body_title = QLabel("", self)
        self._body_title.setObjectName("subtaskPaneBodyTitle")
        self._body_title.setProperty("testid", "subtask-pane-title")
        self._body_title.setTextFormat(Qt.TextFormat.PlainText)
        self._body_title.setWordWrap(True)

        self._header_layout = QHBoxLayout()
        self._header_layout.setContentsMargins(0, 0, 0, 0)
        self._header_layout.setSpacing(6)
        self._header_layout.addWidget(self.btn_toggle)
        self._header_layout.addStretch(1)
        self._header_layout.addWidget(self.btn_add)
        self._header_layout.addWidget(self.btn_clear_done)

        self._empty = QLabel("Selecione uma task", self)
        self._empty.setObjectName("subtaskEmpty")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setWordWrap(True)

        self._list = _SubtaskList(self)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(*_EXPANDED_MARGINS)
        self._layout.setSpacing(8)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layout.addLayout(self._header_layout)
        self._layout.addWidget(self._body_title)
        self._layout.addWidget(self._empty)
        self._layout.addWidget(self._list, 1)

        self.btn_add.clicked.connect(self._add_subtask)
        self.btn_clear_done.clicked.connect(self._clear_done_subtasks)
        self.set_task(None)

    def collapsed_width(self) -> int:
        """Width for collapsed splitter state: toggle button + 2px each side."""
        return self.btn_toggle.sizeHint().width() + _COLLAPSED_MARGINS[0] + _COLLAPSED_MARGINS[2]

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self.btn_toggle.setText("[>]" if collapsed else "[<]")
        self.btn_toggle.setAccessibleName(
            "Expandir painel de subtasks" if collapsed else "Colapsar painel de subtasks"
        )
        self._layout.setContentsMargins(*(_COLLAPSED_MARGINS if collapsed else _EXPANDED_MARGINS))
        self._header_layout.setSpacing(6)
        self.btn_add.setVisible(not collapsed)
        self.btn_clear_done.setVisible(not collapsed)
        self._body_title.setVisible(not collapsed and self._task is not None)
        self._list.setVisible(not collapsed and self._task is not None and self._list.count() > 0)
        self._empty.setVisible(not collapsed and (self._task is None or self._list.count() == 0))
        for row_idx in range(self._list.count()):
            item = self._list.item(row_idx)
            widget = self._list.itemWidget(item)
            if isinstance(widget, _SubtaskRow):
                widget.set_compact(collapsed)
        collapsed_width = self.collapsed_width()
        target_width = collapsed_width if collapsed else _EXPANDED_WIDTH
        self.setMinimumWidth(target_width)
        self.setMaximumWidth(target_width)
        self.updateGeometry()

    def set_task(self, task: Task | None) -> None:
        self._task = task
        self.btn_add.setEnabled(task is not None)
        self.btn_clear_done.setEnabled(False)
        self._body_title.setText("" if task is None else f"Subtasks #{task.id}")
        self._body_title.setVisible(task is not None)
        self.refresh()

    def refresh(self) -> None:
        self._list.clear()
        if self._task is None or self._repo is None:
            self._empty.setText("Selecione uma task")
            self._empty.show()
            self._list.hide()
            self._set_clear_done_enabled(False)
            return
        subtasks = self._repo.list_subtasks(self._task.id)
        if not subtasks:
            self._empty.setText("")
            self._empty.show()
            self._list.hide()
            self._set_clear_done_enabled(False)
            return
        self._empty.hide()
        self._list.show()
        for subtask in subtasks:
            self._add_item(subtask)
        self._set_clear_done_enabled(any(subtask.state == 2 for subtask in subtasks))

    def persist_order(self) -> None:
        if self._repo is None:
            return
        pairs = []
        for row in range(self._list.count()):
            item = self._list.item(row)
            pairs.append((str(item.data(_ROLE_SUBTASK_ID)), row + 1))
        self._repo.update_subtask_order_indexes(pairs)

    def _add_item(self, subtask: Subtask) -> None:
        item = QListWidgetItem()
        item.setData(_ROLE_SUBTASK_ID, subtask.id)
        item.setData(_ROLE_TEXT, subtask.text)
        item.setFlags(
            Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsDragEnabled
        )
        item.setSizeHint(QSize(1, self._row_height(subtask.text, expanded=False)))
        self._list.addItem(item)

        row = _SubtaskRow(
            subtask,
            self._save_subtask_notes,
            lambda expanded, i=item, s=subtask: self._resize_subtask_item(i, s, expanded),
            self._list,
        )
        row.checkbox.stateChanged.connect(lambda state, s=subtask, r=row: self._set_state(s, r, state))
        row.set_compact(self._collapsed)
        self._list.setItemWidget(item, row)

    def _row_height(self, text: str, expanded: bool = False) -> int:
        if len(text) > 70:
            base = 82
        elif len(text) > 34:
            base = 58
        else:
            base = 38
        return base + (78 if expanded else 0)

    def _resize_subtask_item(self, item: QListWidgetItem, subtask: Subtask, expanded: bool) -> None:
        item.setSizeHint(QSize(1, self._row_height(subtask.text, expanded=expanded)))

    def _save_subtask_notes(self, subtask: Subtask, notes: str) -> None:
        if self._repo is not None:
            self._repo.update_subtask_notes(subtask.id, notes)

    def _save_subtask_text(self, subtask: Subtask) -> None:
        if self._repo is None:
            return
        self._repo._conn.execute(
            "UPDATE subtasks SET text = ? WHERE id = ?",
            (subtask.text, subtask.id),
        )
        self._repo._conn.commit()
        self.refresh()

    def _set_state(self, subtask: Subtask, row: _SubtaskRow, qt_state: int) -> None:
        # QCheckBox tri-state usa 0/1/2, exatamente o ciclo pedido.
        state = int(qt_state)
        row.apply_state(state)
        if self._repo is not None:
            self._repo.update_subtask_state(subtask.id, state)
        self._set_clear_done_enabled(self._has_done_subtasks_in_view())

    def _add_subtask(self) -> None:
        if self._task is None or self._repo is None:
            return
        text, ok = QInputDialog.getText(self, "Nova subtask", "Texto da subtask:")
        text = text.strip()
        if not ok or not text:
            return
        next_order = self._list.count() + 1
        subtask = Subtask(
            id=f"st-{uuid.uuid4().hex[:10]}",
            task_id=self._task.id,
            text=text,
            color=random.choice(_COLORS),
            order_index=next_order,
        )
        self._repo.create_subtask(subtask)
        self.refresh()

    def _clear_done_subtasks(self) -> None:
        if self._task is None or self._repo is None:
            return
        self._repo.delete_done_subtasks(self._task.id)
        self.refresh()

    def _has_done_subtasks_in_view(self) -> bool:
        for row_idx in range(self._list.count()):
            item = self._list.item(row_idx)
            widget = self._list.itemWidget(item)
            if isinstance(widget, _SubtaskRow) and widget._subtask.state == 2:
                return True
        return False

    def _set_clear_done_enabled(self, enabled: bool) -> None:
        self.btn_clear_done.setEnabled(enabled)
        if enabled:
            self.btn_clear_done.setToolTip("Limpar subtasks concluídas deste grupo")
        else:
            self.btn_clear_done.setToolTip("Nenhuma subtask concluída neste grupo")
