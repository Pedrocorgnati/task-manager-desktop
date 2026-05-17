from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from task_manager_desktop.ui.empty_state import EmptyStateLabel


def test_renders_text_and_hint(qtbot):
    w = EmptyStateLabel("Sem tasks.", "Atalho: Ctrl+N")
    qtbot.addWidget(w)
    w.show()
    labels = w.findChildren(QLabel)
    texts = [lbl.text() for lbl in labels]
    assert "Sem tasks." in texts
    assert "Atalho: Ctrl+N" in texts


def test_renders_only_main_text_when_hint_none(qtbot):
    w = EmptyStateLabel("Selecione uma task.")
    qtbot.addWidget(w)
    w.show()
    labels = w.findChildren(QLabel)
    assert len(labels) == 1
    assert labels[0].text() == "Selecione uma task."


def test_main_text_is_centered(qtbot):
    w = EmptyStateLabel("hello")
    qtbot.addWidget(w)
    main_label = w.findChild(QLabel)
    assert main_label is not None
    assert bool(main_label.alignment() & Qt.AlignmentFlag.AlignCenter)
