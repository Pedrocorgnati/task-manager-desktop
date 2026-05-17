from __future__ import annotations

import os

import pytest
from PySide6.QtCore import QCoreApplication, QSettings, QSize
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QLabel, QSplitter

from task_manager_desktop.ui.main_window import MainWindowShell


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


def test_splitter_has_two_panels_with_4060_ratio(qtbot):
    w = MainWindowShell()
    qtbot.addWidget(w)
    w.show()
    splitter = w.centralWidget()
    assert isinstance(splitter, QSplitter)
    assert splitter.count() == 2
    # Tolerância de ±5px por handleWidth e arredondamento Qt
    sizes = splitter.sizes()
    assert abs(sizes[0] - 560) <= 5
    assert abs(sizes[1] - 840) <= 5


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
    assert w._splitter.widget(1) is new_widget


@pytest.mark.skipif(
    os.environ.get("QT_QPA_PLATFORM") == "offscreen",
    reason="Geometry persistence requer display real (resize nao e aplicado em offscreen)",
)
def test_qsettings_persistence(qtbot):
    w1 = MainWindowShell()
    qtbot.addWidget(w1)
    w1.show()
    w1.resize(1600, 1000)
    w1._splitter.setSizes([640, 960])
    w1.close()

    w2 = MainWindowShell()
    qtbot.addWidget(w2)
    w2.show()
    assert w2.size() == QSize(1600, 1000)
    # Tolerância de ±5px por handleWidth e arredondamento Qt
    sizes2 = w2._splitter.sizes()
    assert abs(sizes2[0] - 640) <= 5
    assert abs(sizes2[1] - 960) <= 5


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
