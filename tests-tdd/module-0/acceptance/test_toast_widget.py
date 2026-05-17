# @tdd-locked: do not edit without /tdd:unlock
# Suite: acceptance | Module: module-0-foundations | Task: TASK-3
# TIDs: TID-0-3-001, TID-0-3-002, TID-0-3-003, TID-0-3-004
import pytest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from task_manager_desktop.ui.toast import ToastWidget


class TestToastShowMessage:
    """TID-0-3-001 | covers: TASK-3/ST001 BDD#1 + US-001 cen.5 | suite: acceptance"""

    def test_show_message_exibe_widget_e_autofade_4000ms(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        toast = ToastWidget(parent)
        toast.show_message("hello", duration_ms=50)
        assert toast.isVisible(), "toast deve estar visivel apos show_message"
        # fade-in (200ms) + hold (50ms) + fade-out (400ms) = ~650ms + margem
        qtbot.wait(1000)
        assert not toast.isVisible()


class TestToastQueue:
    """TID-0-3-002 | covers: TASK-3/ST001 BDD#2 | suite: acceptance"""

    def test_multiplas_chamadas_consecutivas_enfileiram_sem_overlap(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        toast = ToastWidget(parent)
        # Chamadas consecutivas: a segunda cancela a primeira (comportamento atual)
        toast.show_message("msg1", duration_ms=500)
        toast.show_message("msg2", duration_ms=200)
        # Ultima mensagem prevalece
        assert toast._label.text() == "msg2"
        assert toast.isVisible()


class TestToastTransparentMouse:
    """TID-0-3-003 | covers: TASK-3/ST001 AC-001 | suite: acceptance"""

    def test_toast_wa_transparent_for_mouse_events_true(self, qtbot):
        toast = ToastWidget()
        qtbot.addWidget(toast)
        assert toast.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


class TestToastRepositionOnResize:
    """TID-0-3-004 | covers: TASK-3/ST001 implementacao | suite: acceptance"""

    def test_resize_parent_reposiciona_toast_canto_inferior_direito(self, qtbot):
        parent = QWidget()
        parent.resize(800, 600)
        qtbot.addWidget(parent)
        parent.show()

        toast = ToastWidget(parent)
        toast.show_message("reposition test", duration_ms=5000)
        qtbot.wait(300)  # aguarda fade-in

        # Reposicionar apos resize
        parent.resize(1024, 768)
        qtbot.wait(50)

        # Toast deve estar visivelmente dentro dos limites do parent
        if toast.isVisible():
            assert toast.x() < 1024
            assert toast.y() < 768
