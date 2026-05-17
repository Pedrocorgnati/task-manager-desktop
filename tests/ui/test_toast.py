from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow

from task_manager_desktop.ui.toast import ToastWidget


def test_show_message_makes_widget_visible(qtbot):
    parent = QMainWindow()
    qtbot.addWidget(parent)
    parent.show()
    toast = ToastWidget(parent)
    toast.show_message("hello", duration_ms=4000)
    qtbot.wait(250)
    assert toast.isVisible()


def test_show_message_holds_for_duration(qtbot):
    parent = QMainWindow()
    qtbot.addWidget(parent)
    parent.show()
    toast = ToastWidget(parent)
    toast.show_message("hello", duration_ms=4000)
    qtbot.wait(4000)
    assert toast.isVisible()


def test_toast_does_not_capture_mouse(qtbot):
    parent = QMainWindow()
    qtbot.addWidget(parent)
    parent.show()
    toast = ToastWidget(parent)
    toast.show_message("hello")
    assert toast.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


def test_toast_repositions_on_parent_resize(qtbot):
    parent = QMainWindow()
    qtbot.addWidget(parent)
    parent.resize(800, 600)
    parent.show()
    toast = ToastWidget(parent)
    toast.show_message("hello")
    qtbot.wait(50)
    initial_pos = toast.pos()
    parent.resize(1200, 900)
    qtbot.wait(50)
    assert toast.pos() != initial_pos


def test_consecutive_show_messages_restarts_animation(qtbot):
    parent = QMainWindow()
    qtbot.addWidget(parent)
    parent.show()
    toast = ToastWidget(parent)
    toast.show_message("first")
    toast.show_message("second")
    label = toast.findChild(QLabel)
    assert label is not None
    assert label.text() == "second"
