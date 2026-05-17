# @tdd-locked: do not edit without /tdd:unlock
# Suite: acceptance | Module: module-0-foundations | Task: TASK-3
# TIDs: TID-0-3-010, TID-0-3-011
import pytest

from PySide6.QtWidgets import QLabel

from task_manager_desktop.ui.empty_state import EmptyStateLabel


class TestEmptyStateLabelWithHint:
    """TID-0-3-010 | covers: TASK-3/ST003 BDD#1 | suite: acceptance"""

    def test_empty_state_label_com_hint_action_renderiza_ambos_textos(self, qtbot):
        w = EmptyStateLabel("Sem tasks", hint="Clique +")
        qtbot.addWidget(w)
        w.show()
        labels = w.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        assert "Sem tasks" in texts
        assert "Clique +" in texts


class TestEmptyStateLabelWithoutHint:
    """TID-0-3-011 | covers: TASK-3/ST003 BDD#2 + US-015 | suite: acceptance"""

    def test_empty_state_label_sem_hint_action_nao_exibe_placeholder(self, qtbot):
        w = EmptyStateLabel("Sem tasks")
        qtbot.addWidget(w)
        w.show()
        assert w._hint_label is None, "hint_label nao deve ser criado quando hint=None"
        labels = w.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        assert "Sem tasks" in texts
        assert len(texts) == 1, "Apenas 1 label sem hint"
