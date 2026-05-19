from __future__ import annotations

import pytest
from PySide6.QtWidgets import QComboBox, QLineEdit, QPushButton, QToolButton

from task_manager_desktop.ui.header import HeaderBar


def test_layout_has_required_widgets(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    assert isinstance(bar.btn_new, QPushButton)
    assert isinstance(bar._search, QLineEdit)
    assert isinstance(bar._project_filter, QComboBox)
    assert isinstance(bar._btn_clear_done, QPushButton)
    assert isinstance(bar._btn_trash, QToolButton)


def test_search_placeholder(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    assert bar._search.placeholderText() == "Buscar por título ou notas... (Ctrl+F)"


def test_search_debounce_emits_once(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.search_text_changed, timeout=500) as blocker:
        bar._search.setText("ab")
        bar._search.setText("abc")
    assert blocker.args == ["abc"]


def test_set_projects_initial(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    bar.set_projects(["b", "a"])
    items = [bar._project_filter.itemText(i) for i in range(bar._project_filter.count())]
    assert items == ["Todos", "a", "b"]


def test_set_projects_preserves_selection(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    bar.set_projects(["alpha", "beta", "gamma"])
    bar._project_filter.setCurrentText("beta")
    bar.set_projects(["alpha", "beta", "delta"])
    assert bar._project_filter.currentText() == "beta"


def test_set_projects_falls_back_to_todos_when_missing(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    bar.set_projects(["alpha", "beta"])
    bar._project_filter.setCurrentText("alpha")
    bar.set_projects(["beta", "gamma"])
    assert bar._project_filter.currentText() == "Todos"


def test_current_project_maps_todos_to_none(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    assert bar.current_project() is None
    bar.set_projects(["alpha"])
    bar._project_filter.setCurrentText("alpha")
    assert bar.current_project() == "alpha"


def test_clear_search_emits_empty(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    bar._search.setText("xx")
    qtbot.wait(200)
    with qtbot.waitSignal(bar.search_text_changed, timeout=500) as blocker:
        bar.clear_search()
    assert blocker.args == [""]


def test_focus_search_does_not_clear_text(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    bar._search.setText("preserved")
    bar.focus_search()
    assert bar._search.text() == "preserved"


def test_clear_done_button_emits(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    bar.set_clear_done_enabled(True)  # Enable button before clicking
    with qtbot.waitSignal(bar.clear_completed_clicked, timeout=200):
        bar._btn_clear_done.click()


def test_trash_button_emits(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.trash_clicked, timeout=200):
        bar._btn_trash.click()


def test_ctrl_n_shortcut_registered(qtbot):
    from PySide6.QtGui import QShortcut
    from PySide6.QtWidgets import QMainWindow

    win = QMainWindow()
    bar = HeaderBar(win)
    bar.install_shortcut(win)
    qtbot.addWidget(win)
    shortcuts = win.findChildren(QShortcut)
    sequences = {s.key().toString() for s in shortcuts}
    assert "Ctrl+N" in sequences


def test_clear_done_button_disabled_by_default(qtbot):
    """Button starts disabled."""
    bar = HeaderBar()
    qtbot.addWidget(bar)
    assert not bar._btn_clear_done.isEnabled()


def test_clear_done_button_enabled_when_has_visible_done(qtbot):
    """Button enabled after set_clear_done_enabled(True)."""
    bar = HeaderBar()
    qtbot.addWidget(bar)
    bar.set_clear_done_enabled(True)
    assert bar._btn_clear_done.isEnabled()


def test_clear_done_button_disabled_when_no_visible_done(qtbot):
    """Button disabled after set_clear_done_enabled(False)."""
    bar = HeaderBar()
    qtbot.addWidget(bar)
    bar.set_clear_done_enabled(True)
    bar.set_clear_done_enabled(False)
    assert not bar._btn_clear_done.isEnabled()


def test_clear_done_button_tooltip_when_disabled(qtbot):
    """Tooltip shows when button disabled."""
    bar = HeaderBar()
    qtbot.addWidget(bar)
    bar.set_clear_done_enabled(False)
    assert "Nenhuma task concluída visível" in bar._btn_clear_done.toolTip()


def test_clear_done_button_tooltip_when_enabled(qtbot):
    """Tooltip is empty when button enabled (label is self-explanatory)."""
    bar = HeaderBar()
    qtbot.addWidget(bar)
    bar.set_clear_done_enabled(True)
    assert bar._btn_clear_done.toolTip() == ""


def test_clear_done_button_has_text_label(qtbot):
    """Button shows text 'Limpar concluídas' (not icon-only)."""
    bar = HeaderBar()
    qtbot.addWidget(bar)
    assert bar._btn_clear_done.text() == "Limpar concluídas"


def test_trash_button_tooltip(qtbot):
    """Trash button has correct tooltip."""
    bar = HeaderBar()
    qtbot.addWidget(bar)
    assert bar._btn_trash.toolTip() == "Lixeira (tasks ocultas até 30 dias)"


def test_clear_done_accessible_name_disabled(qtbot):
    """Accessible name includes '(nenhuma disponível)' when disabled."""
    bar = HeaderBar()
    qtbot.addWidget(bar)
    assert "nenhuma disponível" in bar._btn_clear_done.accessibleName()


def test_clear_done_accessible_name_enabled(qtbot):
    """Accessible name is the action label when enabled."""
    bar = HeaderBar()
    qtbot.addWidget(bar)
    bar.set_clear_done_enabled(True)
    assert bar._btn_clear_done.accessibleName() == "Mover tasks concluídas para a Lixeira"
