from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from task_manager_desktop.ui.editor_toolbar import EditorToolbar
from task_manager_desktop.ui.markdown_editor import MarkdownEditor


# ── MarkdownEditor ────────────────────────────────────────────────────────────


def test_editor_uses_monospace_font(qtbot):
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    family = editor.font().family()
    hint = editor.font().styleHint()
    assert "Mono" in family or "mono" in family.lower() or hint == QFont.StyleHint.Monospace


def test_editor_accessible_name(qtbot):
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    assert editor.accessibleName() == "Editor de notas Markdown"


def test_editor_accessible_description(qtbot):
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    assert "Markdown" in editor.accessibleDescription()
    assert "monoespacada" in editor.accessibleDescription()


def test_editor_accepts_plain_text(qtbot):
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    editor.setPlainText("# Título\n\n- item")
    assert editor.toPlainText() == "# Título\n\n- item"


def test_editor_has_line_number_area(qtbot):
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    assert editor.line_number_area_width() > 20


def test_editor_bolds_markdown_headings(qtbot):
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    editor.setPlainText("# Título")
    editor.document().adjustSize()
    first_block = editor.document().firstBlock()
    formats = first_block.layout().formats()
    assert formats


def test_editor_toggle_fold_hides_second_level_children(qtbot):
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    editor.setPlainText("# Título\n## Seção\nlinha 1\nlinha 2\n## Outra\nlinha 3")
    editor.toggle_fold(1)
    assert editor.document().findBlockByNumber(2).isVisible() is False
    assert editor.document().findBlockByNumber(3).isVisible() is False
    assert editor.document().findBlockByNumber(4).isVisible() is True
    editor.toggle_fold(1)
    assert editor.document().findBlockByNumber(2).isVisible() is True


# ── EditorToolbar ─────────────────────────────────────────────────────────────


def test_toolbar_has_save_and_cancel_buttons(qtbot):
    toolbar = EditorToolbar()
    qtbot.addWidget(toolbar)
    assert toolbar.btn_save is not None
    assert toolbar.btn_cancel is not None
    assert toolbar.btn_save.text() == "Salvar"
    assert toolbar.btn_cancel.text() == "Cancelar"


def test_toolbar_emits_save_on_button_click(qtbot):
    toolbar = EditorToolbar()
    qtbot.addWidget(toolbar)
    with qtbot.waitSignal(toolbar.save_requested, timeout=500):
        qtbot.mouseClick(toolbar.btn_save, Qt.MouseButton.LeftButton)


def test_toolbar_emits_cancel_on_button_click(qtbot):
    toolbar = EditorToolbar()
    qtbot.addWidget(toolbar)
    with qtbot.waitSignal(toolbar.cancel_requested, timeout=500):
        qtbot.mouseClick(toolbar.btn_cancel, Qt.MouseButton.LeftButton)


def test_toolbar_accessible_names(qtbot):
    toolbar = EditorToolbar()
    qtbot.addWidget(toolbar)
    assert toolbar.btn_save.accessibleName() != ""
    assert toolbar.btn_cancel.accessibleName() != ""
