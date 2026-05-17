from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

from task_manager_desktop.ui.dialogs import ErrorDialog


def test_dialog_displays_three_sections(qtbot):
    dialog = ErrorDialog(None, "Erro de I/O", "OSError(13)", "/tmp/x.db", "Verifique permissoes")
    qtbot.addWidget(dialog)
    labels = dialog.findChildren(QLabel)
    texts = " ".join(lbl.text() for lbl in labels)
    assert "OSError(13)" in texts
    assert "/tmp/x.db" in texts
    assert "Verifique permissoes" in texts


def test_copy_path_button_copies_to_clipboard(qtbot):
    dialog = ErrorDialog(None, "Erro", "desc", "/tmp/x.db", "sug")
    qtbot.addWidget(dialog)
    dialog._on_copy()
    assert QApplication.clipboard().text() == "/tmp/x.db"


def test_copy_button_text_changes_to_copiado(qtbot):
    dialog = ErrorDialog(None, "Erro", "desc", "/tmp/x.db", "sug")
    qtbot.addWidget(dialog)
    dialog.show()
    dialog._on_copy()
    assert dialog._copy_btn.text() == "Copiado!"
    qtbot.wait(2000)  # timer eh 1500ms; margem extra para event loop
    assert dialog._copy_btn.text() == "Copiar caminho"


def test_dialog_is_modal(qtbot):
    dialog = ErrorDialog(None, "Erro", "desc", "/tmp/x.db", "sug")
    qtbot.addWidget(dialog)
    assert dialog.isModal()


def test_show_io_error_classmethod_builds_dialog(qtbot, monkeypatch):
    monkeypatch.setattr(ErrorDialog, "exec", lambda self: 1)
    code = ErrorDialog.show_io_error(None, OSError(13, "Permission denied"), "/tmp/x.db")
    assert code == 1


def test_enter_triggers_accept(qtbot):
    dialog = ErrorDialog(None, "Erro", "desc", "/tmp/x.db", "sug")
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.keyClick(dialog, Qt.Key.Key_Return)
    assert not dialog.isVisible()
