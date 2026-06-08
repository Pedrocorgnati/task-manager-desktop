from __future__ import annotations

import os

import pytest
from PySide6.QtCore import QByteArray, QCoreApplication, QSettings, QSize
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QLabel, QSplitter

from task_manager_desktop.ui.main_window import (
    _SETTINGS_GEOMETRY,
    _SETTINGS_SPLITTER,
    _SETTINGS_STATE,
    MainWindowShell,
)
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


def test_splitter_has_three_panels_with_updated_widths(qtbot):
    w = MainWindowShell()
    qtbot.addWidget(w)
    w.show()
    splitter = w.centralWidget()
    assert isinstance(splitter, QSplitter)
    assert splitter.count() == 3
    # Tolerância de ±5px por handleWidth e arredondamento Qt
    sizes = splitter.sizes()
    assert abs(sizes[0] - 340) <= 8
    assert abs(sizes[1] - 260) <= 8
    assert abs(sizes[2] - 800) <= 8


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
    assert abs(sizes[0] / total - 0.243) < 0.04
    assert abs(sizes[1] / total - 0.05) < 0.03
    assert abs(sizes[2] / total - 0.707) < 0.04
    w.set_middle_collapsed(False)
    sizes = w._splitter.sizes()
    total = sum(sizes)
    assert abs(sizes[1] / total - 0.186) < 0.04


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


def test_qsettings_persistence_via_settings_layer(qtbot):
    """Geometry/state/splitter persistence — testado pela camada QSettings,
    sem depender de um compositor real.

    O teste antigo (test_qsettings_persistence, agora abaixo) afirmava
    `w2.size() == QSize(1600,1000)`, o que exige um compositor: offscreen,
    `restoreGeometry()` reajusta a geometria contra a tela (indefinida) e
    descarta o tamanho exato. Por isso ele ficava `skipif(offscreen)` e o CI
    headless nunca exercitava a persistencia.

    Este teste cobre o contrato real e determinístico:
      (1) closeEvent GRAVA os tres blobs (geometry/state/splitter) em QSettings;
      (2) uma nova janela LE e APLICA esses blobs via _restore_settings sem erro;
      (3) a PROPORCAO do splitter e preservada (proporcoes fazem round-trip
          offscreen; apenas pixels absolutos nao).
    """
    w1 = MainWindowShell()
    qtbot.addWidget(w1)
    w1.show()
    qtbot.waitExposed(w1)
    # Razao deliberadamente assimetrica (~58/12/30%) — distinta dos defaults
    # 35/15/50 — para provar que a proporcao restaurada veio do QSettings.
    w1._splitter.setSizes([580, 120, 300])
    ratio_before = [s / sum(w1._splitter.sizes()) for s in w1._splitter.sizes()]
    w1.close()

    # (1) closeEvent persistiu os tres blobs.
    geometry_blob = QSettings().value(_SETTINGS_GEOMETRY)
    state_blob = QSettings().value(_SETTINGS_STATE)
    splitter_blob = QSettings().value(_SETTINGS_SPLITTER)
    for name, blob in (
        ("geometry", geometry_blob),
        ("state", state_blob),
        ("splitter", splitter_blob),
    ):
        assert isinstance(blob, (bytes, bytearray, QByteArray)), (
            f"closeEvent nao persistiu '{name}' em QSettings"
        )
        assert len(QByteArray(blob)) > 0, f"blob '{name}' persistido vazio"

    # (2) + (3) nova janela le e aplica os blobs; proporcao do splitter sobrevive.
    w2 = MainWindowShell()
    qtbot.addWidget(w2)
    w2.show()
    qtbot.waitExposed(w2)
    ratio_after = [s / sum(w2._splitter.sizes()) for s in w2._splitter.sizes()]
    for i, (before, after) in enumerate(zip(ratio_before, ratio_after)):
        assert abs(before - after) < 0.04, (
            f"proporcao do painel {i} nao foi restaurada: "
            f"{before:.3f} -> {after:.3f}"
        )


@pytest.mark.skipif(
    os.environ.get("QT_QPA_PLATFORM") == "offscreen",
    reason=(
        "Afirma o tamanho EXATO da janela (1600x1000) apos round-trip "
        "saveGeometry/restoreGeometry. Offscreen, restoreGeometry() reajusta a "
        "geometria contra a tela indefinida e descarta os pixels exatos "
        "(verificado: 1600x1000 -> 798x774). A persistencia via camada de "
        "settings ja e coberta por test_qsettings_persistence_via_settings_layer, "
        "que roda por padrao. Rodar este aqui: pytest com QT_QPA_PLATFORM=xcb "
        "(ou wayland) num display real."
    ),
)
def test_qsettings_persistence_exact_pixels(qtbot):
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
    # Aguarda o fechamento efetivar em vez de um sleep arbitrario — o trigger
    # da action enfileira o close; um qtbot.wait() fixo corre com esse evento.
    qtbot.waitUntil(lambda: not w.isVisible(), timeout=1000)


def test_splitter_not_collapsible(qtbot):
    w = MainWindowShell()
    qtbot.addWidget(w)
    assert w._splitter.childrenCollapsible() is False


def test_minimum_size_enforced(qtbot):
    w = MainWindowShell()
    qtbot.addWidget(w)
    w.show()
    assert w.minimumSize() == QSize(900, 600)
