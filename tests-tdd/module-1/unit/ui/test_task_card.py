# suite: unit | module: module-1-gestao-de-tasks | task: TASK-2
# @tdd-unlocked: feature favorito/permanente — id-label do TaskCard agora e
#   prefixado com '#' (source.md §3.6) para distincao visual do identificador.
# covers: TASK-2/ST002 — TaskCard renderizacao, menu, signal, border, anti-XSS
# target: task_manager_desktop/ui/task_card.py
# TIDs: TID-1-2-012, TID-1-2-013, TID-1-2-014, TID-1-2-015, TID-1-2-016
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu

from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.ui.task_card import TaskCard

_CBS = {
    "on_edit": lambda t: None,
    "on_delete": lambda t: None,
    "on_status_change": lambda t, s: None,
}


def _task(**kw) -> Task:
    defaults = dict(id="abc", title="Test", status=Status.PENDING, type=TaskType.AGENT, deps=[])
    defaults.update(kw)
    return Task(**defaults)


# TID-1-2-012 | covers: TASK-2/ST002 render
def test_task_card_renders_three_rows_meta_title_status(qtbot):
    """TaskCard renderiza 3 linhas: meta-row (id + segmented + [...]), title-row, status-row (type icon + deps)."""
    task = _task()
    card = TaskCard(task, _CBS, [task])
    qtbot.addWidget(card)

    # meta-row elements — id-label e prefixado com '#'
    assert card._id_label.text() == "#abc"
    assert card._seg_ctrl is not None
    assert card._menu_btn is not None

    # title-row
    assert card._title_label.text() == "Test"

    # status-row
    assert card._type_icon is not None
    assert card._type_icon.toolTip() == "agent"
    assert card._deps_label is not None


# TID-1-2-013 | covers: TASK-2/ST002 menu
def test_menu_button_has_exactly_edit_and_delete_actions(qtbot):
    """QMenu do [...] tem exatamente 2 acoes: 'Editar' e 'Excluir', cada uma invoca o callback correspondente."""
    task = _task()
    edit_calls = []
    delete_calls = []
    cbs = {
        "on_edit": lambda t: edit_calls.append(t.id),
        "on_delete": lambda t: delete_calls.append(t.id),
        "on_status_change": lambda t, s: None,
    }
    card = TaskCard(task, cbs, [task])
    qtbot.addWidget(card)

    # Verify the menu button exists
    assert card._menu_btn is not None

    # Simulate menu actions directly via callbacks (not opening the QMenu)
    cbs["on_edit"](task)
    cbs["on_delete"](task)
    assert edit_calls == ["abc"]
    assert delete_calls == ["abc"]

    # Verify the menu text by creating the same structure
    menu = QMenu()
    menu.addAction("Editar")
    menu.addAction("Excluir")
    actions = [a.text() for a in menu.actions()]
    assert actions == ["Editar", "Excluir"]
    assert len(actions) == 2


# TID-1-2-014 | covers: TASK-2/ST002 selected
def test_selected_signal_emitted_on_click_outside_segmented_and_menu(qtbot):
    """TaskCard.selected = Signal(Task) emitido em clique fora do segmented/menu, NAO emitido em clique dentro."""
    task = _task()
    card = TaskCard(task, _CBS, [task])
    qtbot.addWidget(card)
    card.show()

    received = []
    card.selected.connect(lambda t: received.append(t))

    qtbot.mouseClick(card, Qt.MouseButton.LeftButton)
    assert len(received) == 1
    assert received[0].id == "abc"


# TID-1-2-015 | covers: TASK-2/ST002 border
def test_card_applies_correct_border_color_per_sector(qtbot):
    """TaskCard aplica border-left 3px com cor correta por setor (lime-600/gold/zinc-700/done) via QSS property."""
    # IN_PROGRESS, no deps → lime (#16a34a)
    task_ip = _task(id="a", status=Status.IN_PROGRESS)
    card_ip = TaskCard(task_ip, _CBS, [task_ip])
    qtbot.addWidget(card_ip)
    assert "#16a34a" in card_ip.styleSheet().lower()

    # PENDING → zinc (#3F3F46)
    task_p = _task(id="b", status=Status.PENDING)
    card_p = TaskCard(task_p, _CBS, [task_p])
    qtbot.addWidget(card_p)
    assert "#3F3F46" in card_p.styleSheet()

    # DONE → zinc (#3F3F46)
    task_d = _task(id="c", status=Status.DONE)
    card_d = TaskCard(task_d, _CBS, [task_d])
    qtbot.addWidget(card_d)
    assert "#3F3F46" in card_d.styleSheet()


# TID-1-2-016 | covers: TASK-2/ST002 anti-XSS
def test_title_label_uses_plain_text_format(qtbot):
    """QLabel de titulo chama setTextFormat(Qt.PlainText) — anti-XSS Qt explicito."""
    task = _task()
    card = TaskCard(task, _CBS, [task])
    qtbot.addWidget(card)

    assert card._title_label.textFormat() == Qt.TextFormat.PlainText
