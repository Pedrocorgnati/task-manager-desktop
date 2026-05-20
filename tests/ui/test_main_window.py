from __future__ import annotations

import os

import pytest
from PySide6.QtCore import QCoreApplication, QSettings, QSize
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QLabel, QSplitter

from task_manager_desktop.ui.main_window import MainWindowShell
from task_manager_desktop.ui.subtask_pane import SubtaskPane


@pytest.fixture(autouse=True)
def _clear_settings():
    QCoreApplication.setOrganizationName("test-org-tmdt")
    QCoreApplication.setApplicationName("test-app-tmdt")
    QSettings().clear()
    yield
    QSettings().clear()


def test_default_window_size_is_1400x900(qtbot):
    w = MainWindowShell()
    qtbot.addWidget(w)
    w.show()
    assert w.size() == QSize(1400, 900)


def test_splitter_has_three_panels_with_351550_ratio(qtbot):
    w = MainWindowShell()
    qtbot.addWidget(w)
    w.show()
    splitter = w.centralWidget()
    assert isinstance(splitter, QSplitter)
    assert splitter.count() == 3
    # Tolerância de ±5px por handleWidth e arredondamento Qt
    sizes = splitter.sizes()
    assert abs(sizes[0] - 490) <= 8
    assert abs(sizes[1] - 210) <= 8
    assert abs(sizes[2] - 700) <= 8


def test_initial_empty_states_visible(qtbot):
    w = MainWindowShell()
    qtbot.addWidget(w)
    w.show()
    labels = w.findChildren(QLabel)
    texts = " ".join(lbl.text() for lbl in labels)
    assert "Sem tasks" in texts
    assert "Selecione uma task" in texts


def test_set_left_widget_replaces_empty_state(qtbot):
    w = MainWindowShell()
    qtbot.addWidget(w)
    w.show()
    new_widget = QLabel("real task list")
    w.set_left_widget(new_widget)
    assert w._splitter.widget(0) is new_widget


def test_set_right_widget_replaces_empty_state(qtbot):
    w = MainWindowShell()
    qtbot.addWidget(w)
    w.show()
    new_widget = QLabel("real markdown viewer")
    w.set_right_widget(new_widget)
    assert w._splitter.widget(2) is new_widget


def test_middle_column_collapses_to_5_percent(qtbot):
    w = MainWindowShell()
    qtbot.addWidget(w)
    w.show()
    w.set_middle_collapsed(True)
    sizes = w._splitter.sizes()
    total = sum(sizes)
    assert w.is_middle_collapsed() is True
    assert abs(sizes[0] / total - 0.35) < 0.04
    assert abs(sizes[1] / total - 0.05) < 0.03
    assert abs(sizes[2] / total - 0.60) < 0.04
    w.set_middle_collapsed(False)
    sizes = w._splitter.sizes()
    total = sum(sizes)
    assert abs(sizes[1] / total - 0.15) < 0.04


def test_subtask_pane_collapses_to_toggle_width_plus_lateral_padding(qtbot):
    w = MainWindowShell()
    qtbot.addWidget(w)
    pane = SubtaskPane()
    w.set_middle_widget(pane)
    w.show()

    w.set_middle_collapsed(True)
    sizes = w._splitter.sizes()
    margins = pane.layout().contentsMargins()

    assert pane.property("testid") == "subtask-pane"
    assert margins.left() == 2
    assert margins.right() == 2
    assert pane.minimumWidth() == pane.collapsed_width()
    assert pane.maximumWidth() == pane.collapsed_width()
    assert abs(sizes[1] - pane.collapsed_width()) <= 2


@pytest.mark.skipif(
    os.environ.get("QT_QPA_PLATFORM") == "offscreen",
    reason="Geometry persistence requer display real (resize nao e aplicado em offscreen)",
)
def test_qsettings_persistence(qtbot):
    w1 = MainWindowShell()
    qtbot.addWidget(w1)
    w1.show()
    w1.resize(1600, 1000)
    w1._splitter.setSizes([560, 240, 800])
    w1.close()

    w2 = MainWindowShell()
    qtbot.addWidget(w2)
    w2.show()
    assert w2.size() == QSize(1600, 1000)
    # Tolerância de ±5px por handleWidth e arredondamento Qt
    sizes2 = w2._splitter.sizes()
    assert abs(sizes2[0] - 560) <= 5
    assert abs(sizes2[1] - 240) <= 5
    assert abs(sizes2[2] - 800) <= 5


def test_dark_theme_applied(qtbot):
    w = MainWindowShell()
    qtbot.addWidget(w)
    w.show()
    qss = w.styleSheet()
    assert "#18181b" in qss.lower() or "#18181B" in qss
    assert "Ubuntu Sans" in qss or "Segoe UI" in qss


def test_ctrl_q_closes_window(qtbot):
    w = MainWindowShell()
    qtbot.addWidget(w)
    w.show()
    # Localiza a action "Sair" (acionada pelo atalho Ctrl+Q) e dispara diretamente
    # — ambiente headless nao processa shortcuts via keyClick de forma confiavel
    sair_action = next(
        (a for a in w.findChildren(QAction) if "Sair" in a.text()), None
    )
    assert sair_action is not None, "Action 'Sair' nao encontrada no menu"
    assert sair_action.shortcut() == QKeySequence("Ctrl+Q")
    sair_action.trigger()
    qtbot.wait(100)
    assert not w.isVisible()


def test_splitter_not_collapsible(qtbot):
    w = MainWindowShell()
    qtbot.addWidget(w)
    assert w._splitter.childrenCollapsible() is False


def test_minimum_size_enforced(qtbot):
    w = MainWindowShell()
    qtbot.addWidget(w)
    w.show()
    assert w.minimumSize() == QSize(900, 600)
