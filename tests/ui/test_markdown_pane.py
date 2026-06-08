from __future__ import annotations

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

import task_manager_desktop.ui.markdown_pane as markdown_pane_module
from task_manager_desktop.core.models import Status, Task
from task_manager_desktop.ui.markdown_pane import MarkdownPane


def _make_task(task_id: str = "t1", notes: str = "# Nota") -> Task:
    return Task(
        id=task_id,
        title=f"Task {task_id}",
        status=Status.PENDING,
        deps=[],
        notes=notes,
        order_index=0,
    )


@pytest.fixture
def pane(qtbot):
    w = MarkdownPane()
    qtbot.addWidget(w)
    return w


@pytest.fixture
def sample_task() -> Task:
    return _make_task("ta", "# Original")


@pytest.fixture
def sample_task_b() -> Task:
    return _make_task("tb", "# Nota B")


# ── Estrutura inicial ─────────────────────────────────────────────────────────


def test_initial_stack_shows_viewer(pane):
    assert pane.stack.currentIndex() == 0


def test_btn_edit_hidden_when_no_task(pane):
    pane.set_task(None)
    assert not pane.btn_edit.isVisible()


def test_btn_edit_visible_after_set_task(pane, sample_task):
    pane.set_task(sample_task)
    assert not pane.btn_edit.isVisibleTo(pane)
    assert pane.toolbar.btn_save.isEnabled()
    assert pane.toolbar.btn_toggle.isEnabled()


# ── Transição viewer → editor ────────────────────────────────────────────────


def test_edit_button_switches_to_editor(qtbot, pane, sample_task):
    pane.show()
    with qtbot.waitSignal(pane.editing_changed) as blocker:
        pane.set_task(sample_task)
    assert blocker.args == [True]
    assert pane.stack.currentIndex() == 1
    assert pane.editor.toPlainText() == sample_task.notes
    pane.hide()


# ── Cancel descarta e volta ao viewer ────────────────────────────────────────


def test_cancel_returns_to_viewer_with_original(qtbot, pane, sample_task):
    pane.show()
    pane.set_task(sample_task)
    pane.editor.setPlainText("# modificado")
    with qtbot.waitSignal(pane.editing_changed) as blocker:
        pane.toolbar.cancel_requested.emit()
    assert blocker.args == [False]
    assert pane.stack.currentIndex() == 0
    pane.toolbar.toggle_preview_requested.emit()
    assert pane.editor.toPlainText() == sample_task.notes
    pane.hide()


# ── set_task reseta para viewer ───────────────────────────────────────────────


def test_set_task_resets_to_viewer(qtbot, pane, sample_task, sample_task_b):
    pane.show()
    pane.set_task(sample_task)
    assert pane.stack.currentIndex() == 1
    pane.set_task(sample_task_b)
    assert pane.stack.currentIndex() == 1
    pane.hide()


def test_set_task_none_hides_edit_button(pane, sample_task):
    pane.set_task(sample_task)
    assert not pane.btn_edit.isVisibleTo(pane)
    pane.set_task(None)
    assert not pane.btn_edit.isVisibleTo(pane)


# ── editing_changed emitido em toda transição ─────────────────────────────────


def test_editing_changed_emitted_true_on_edit(qtbot, pane, sample_task):
    pane.show()
    signals = []
    pane.editing_changed.connect(signals.append)
    pane.set_task(sample_task)
    assert signals == [True]
    pane.hide()


def test_editing_changed_emitted_false_on_cancel(qtbot, pane, sample_task):
    pane.show()
    pane.set_task(sample_task)
    signals = []
    pane.editing_changed.connect(signals.append)
    pane.toolbar.cancel_requested.emit()
    assert signals == [False]
    pane.hide()


def test_reader_theme_toggle_changes_editor_palette(qtbot, pane, sample_task):
    pane.show()
    pane.set_task(sample_task)
    assert pane.reader_light_mode() is False
    pane.toolbar.btn_reader_theme.click()
    assert pane.reader_light_mode() is True
    assert pane.editor.palette().base().color().name().lower() == "#fafaf7"
    assert pane.editor.palette().text().color().name().lower() == "#111116"
    pane.toolbar.btn_reader_theme.click()
    assert pane.reader_light_mode() is False
    assert pane.editor.palette().base().color().name().lower() == "#0d0e12"
    pane.hide()


def test_reader_font_buttons_persist_delta(qtbot, sample_task):
    settings = QSettings()
    settings.remove(markdown_pane_module._SETTINGS_READER_FONT_DELTA)
    try:
        pane = MarkdownPane()
        qtbot.addWidget(pane)
        pane.set_task(sample_task)

        pane.toolbar.btn_reader_font_increase.click()
        pane.toolbar.btn_reader_font_increase.click()

        assert pane.reader_font_delta() == 2
        assert pane.editor.font().pixelSize() == 15
        assert settings.value(markdown_pane_module._SETTINGS_READER_FONT_DELTA, type=int) == 2

        pane2 = MarkdownPane()
        qtbot.addWidget(pane2)
        pane2.set_task(sample_task)

        assert pane2.reader_font_delta() == 2
        assert pane2.editor.font().pixelSize() == 15
    finally:
        settings.remove(markdown_pane_module._SETTINGS_READER_FONT_DELTA)


def test_external_paste_button_is_floating_submit_style(qtbot, pane, sample_task):
    pane.resize(520, 420)
    pane.show()
    pane.set_task(sample_task)
    qtbot.wait(0)

    button = pane.external_paste_button
    assert button.property("testid") == "markdown-external-paste-button"
    assert button.isVisibleTo(pane)
    assert not button.icon().isNull()
    assert button.width() == button.height() == 56
    assert button.geometry().right() <= pane.stack.geometry().right()
    assert button.geometry().bottom() <= pane.stack.geometry().bottom()
    pane.hide()


class _FakeProc:
    def __init__(self, returncode: int = 0) -> None:
        self._returncode = returncode

    def poll(self) -> int:
        return self._returncode


def test_external_paste_button_pastes_current_markdown_after_delay(
    qtbot,
    monkeypatch,
    pane,
    sample_task,
):
    calls = []

    def fake_popen(args, **kwargs):
        calls.append((args, kwargs))
        return _FakeProc()

    monkeypatch.setattr(markdown_pane_module, "_EXTERNAL_PASTE_DELAY_MS", 1)
    # Alvo nao-terminal -> Ctrl+V. Detecção isolada para nao depender de X server.
    monkeypatch.setattr(MarkdownPane, "_detect_paste_shortcut", lambda self: "ctrl+v")
    monkeypatch.setattr(markdown_pane_module.subprocess, "Popen", fake_popen)

    pane.show()
    pane.set_task(sample_task)
    pane.editor.setPlainText("# Rascunho\n\ntexto atual")

    pane.external_paste_button.click()

    qtbot.waitUntil(lambda: bool(calls), timeout=500)
    assert QApplication.clipboard().text() == "# Rascunho\n\ntexto atual"
    assert calls[0][0] == ["xdotool", "key", "--clearmodifiers", "ctrl+v"]
    pane.hide()


def test_external_paste_uses_non_blocking_popen_not_run(
    qtbot, monkeypatch, pane, sample_task
):
    """Regressao: o paste NUNCA pode usar subprocess.run (bloqueia o event loop
    do Qt e impede servir o clipboard X11 sem um clipboard manager)."""
    popen_calls = []
    run_called = []

    monkeypatch.setattr(markdown_pane_module, "_EXTERNAL_PASTE_DELAY_MS", 1)
    monkeypatch.setattr(MarkdownPane, "_detect_paste_shortcut", lambda self: "ctrl+v")
    monkeypatch.setattr(
        markdown_pane_module.subprocess,
        "Popen",
        lambda args, **kw: popen_calls.append(args) or _FakeProc(),
    )
    monkeypatch.setattr(
        markdown_pane_module.subprocess,
        "run",
        lambda *a, **k: run_called.append(a) or object(),
    )

    pane.show()
    pane.set_task(sample_task)
    pane.editor.setPlainText("conteudo")
    pane.external_paste_button.click()

    qtbot.waitUntil(lambda: bool(popen_calls), timeout=500)
    assert popen_calls, "esperava Popen (nao-bloqueante)"
    assert run_called == [], "subprocess.run bloquearia o event loop do Qt"
    pane.hide()


def test_external_paste_detects_terminal_and_uses_ctrl_shift_v(
    qtbot, monkeypatch, pane, sample_task
):
    """Terminais colam com Ctrl+Shift+V (paste do clipboard) na janela focada."""
    calls = []

    def fake_run(args, **kwargs):
        out = ""
        if args[:2] == ["xdotool", "getactivewindow"]:
            out = "12345\n"
        elif args[0] == "xprop":
            out = 'WM_CLASS(STRING) = "gnome-terminal-server", "Gnome-terminal"\n'

        class _R:
            stdout = out
        return _R()

    monkeypatch.setattr(markdown_pane_module, "_EXTERNAL_PASTE_DELAY_MS", 1)
    monkeypatch.setattr(markdown_pane_module.subprocess, "run", fake_run)
    monkeypatch.setattr(
        markdown_pane_module.subprocess,
        "Popen",
        lambda args, **kw: calls.append(args) or _FakeProc(),
    )

    pane.show()
    pane.set_task(sample_task)
    pane.editor.setPlainText("texto p/ terminal")
    pane.external_paste_button.click()

    qtbot.waitUntil(lambda: bool(calls), timeout=500)
    assert calls[0] == ["xdotool", "key", "--clearmodifiers", "ctrl+shift+v"]
    pane.hide()


def test_detect_paste_shortcut_falls_back_to_ctrl_v_on_failure(monkeypatch, pane):
    """Sem xdotool/xprop (FileNotFoundError) a deteccao nao trava: cai no Ctrl+V."""
    def boom(*a, **k):
        raise FileNotFoundError

    monkeypatch.setattr(markdown_pane_module.subprocess, "run", boom)
    assert pane._detect_paste_shortcut() == "ctrl+v"
