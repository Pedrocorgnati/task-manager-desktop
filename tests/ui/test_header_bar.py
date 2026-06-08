from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QCheckBox, QPushButton, QToolButton

import task_manager_desktop.ui.header as header_module
from task_manager_desktop.core.models import TaskType
from task_manager_desktop.ui.header import HeaderBar


def test_layout_has_required_widgets(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    assert isinstance(bar.btn_new, QPushButton)
    assert not hasattr(bar, "_search")
    assert all(isinstance(cb, QCheckBox) for cb in bar._type_checkboxes.values())
    assert isinstance(bar._btn_clear_done, QToolButton)
    assert isinstance(bar._btn_terminal_layout, QToolButton)
    assert isinstance(bar._btn_terminal_collapse, QToolButton)
    assert isinstance(bar._btn_trash, QToolButton)


def test_docs_and_lessie_prompts_have_distinct_icons(qtbot):
    # Os dois botoes vizinhos (documentos e prompts do Lessie) usavam o mesmo
    # glifo; agora devem renderizar icones distintos.
    from PySide6.QtCore import QSize

    bar = HeaderBar()
    qtbot.addWidget(bar)
    docs_img = bar._btn_docs.icon().pixmap(QSize(20, 20)).toImage()
    lessie_img = bar._btn_lessie_prompts.icon().pixmap(QSize(20, 20)).toImage()
    assert not docs_img.isNull()
    assert not lessie_img.isNull()
    assert docs_img != lessie_img


def test_type_filter_defaults_to_all_selected(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    assert bar.current_task_types() == frozenset(t.value for t in TaskType)


def test_type_filter_emits_selected_types(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.type_filter_changed, timeout=200) as blocker:
        bar._type_checkboxes["dev"].setChecked(False)
    assert blocker.args == [frozenset({"human", "agent"})]


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


def test_terminal_layout_button_emits_toggle(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.terminal_layout_mode_toggled, timeout=200) as blocker:
        bar._btn_terminal_layout.click()
    assert blocker.args == [True]


def test_terminal_collapse_button_emits(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.terminal_collapse_requested, timeout=200):
        bar._btn_terminal_collapse.click()


def test_datatest_buttons_use_short_labels(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    assert bar._btn_datatest.text() == "Main"
    assert bar._btn_bodytest.text() == "Body"
    assert bar._btn_btntest.text() == "Btn"


def test_datatest_terminal_checkbox_emits_toggle(qtbot):
    bar = HeaderBar()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.datatest_terminal_write_toggled, timeout=200) as blocker:
        bar._datatest_terminal_checkbox.setChecked(True)
    assert blocker.args == [True]
    assert bar.is_terminal_write_enabled() is True


def test_forge_pick_launches_from_systemforge_root(qtbot, monkeypatch):
    calls = []

    def fake_popen(args, **kwargs):
        calls.append((args, kwargs))
        return object()

    monkeypatch.setattr(header_module.subprocess, "Popen", fake_popen)

    bar = HeaderBar()
    qtbot.addWidget(bar)
    bar._open_forge_pick_tool()

    expected_root = Path(header_module.__file__).resolve().parents[4]
    assert calls == [
        (
            ["python3", str(expected_root / "ai-forge" / "forge-pick" / "app.py")],
            {"cwd": str(expected_root), "start_new_session": True},
        )
    ]


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
    assert (
        "Sem tasks concluídas não-permanentes para ocultar"
        in bar._btn_clear_done.toolTip()
    )


def test_clear_done_button_tooltip_when_enabled(qtbot):
    """Tooltip describes the icon-only action when enabled."""
    bar = HeaderBar()
    qtbot.addWidget(bar)
    bar.set_clear_done_enabled(True)
    assert bar._btn_clear_done.toolTip() == "Mover tasks concluídas para a Lixeira"


def test_clear_done_button_is_icon_only(qtbot):
    """Button uses broom icon instead of text label."""
    bar = HeaderBar()
    qtbot.addWidget(bar)
    assert bar._btn_clear_done.text() == ""
    assert not bar._btn_clear_done.icon().isNull()


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
