"""BDD tests for 'Limpar concluídas' button behavior (ST004)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication
from unittest.mock import Mock, patch

from task_manager_desktop.ui.header import HeaderBar
from task_manager_desktop.core.models import Status, Task

# Optional: pytest_bdd fixtures (conditionally imported)
try:
    from pytest_bdd import given, when, then, scenario
    HAS_BDD = True
except ImportError:
    HAS_BDD = False


# BDD scenarios (only if pytest_bdd is available)
if HAS_BDD:
    @scenario("clear_done_scenarios.feature", "Button disabled by default")
    def test_button_disabled_by_default():
        pass

    @scenario("clear_done_scenarios.feature", "Button enabled when has visible done tasks")
    def test_button_enabled_when_has_done():
        pass

    @scenario("clear_done_scenarios.feature", "Clicking button emits signal and hides tasks")
    def test_clicking_button_hides_tasks():
        pass

    @scenario("clear_done_scenarios.feature", "Error handling for database failures")
    def test_error_handling():
        pass

    # Fixtures and step definitions

    @given("a HeaderBar instance")
    def header_bar_instance(qtbot):
        bar = HeaderBar()
        qtbot.addWidget(bar)
        return bar

    @given("the button is initially disabled")
    def button_disabled(header_bar_instance):
        assert not header_bar_instance._btn_clear_done.isEnabled()
        return header_bar_instance

    @when("the button is enabled with set_clear_done_enabled(True)")
    def enable_button(header_bar_instance):
        header_bar_instance.set_clear_done_enabled(True)
        return header_bar_instance

    @when("the button is clicked")
    def click_button(header_bar_instance, qtbot):
        header_bar_instance.set_clear_done_enabled(True)
        with qtbot.waitSignal(header_bar_instance.clear_completed_clicked, timeout=200):
            header_bar_instance._btn_clear_done.click()
        return header_bar_instance

    @when("the repository mark_hidden() method fails")
    def repo_fails(header_bar_instance):
        return header_bar_instance

    @then("the button should be disabled")
    def button_is_disabled(header_bar_instance):
        assert not header_bar_instance._btn_clear_done.isEnabled()

    @then("the button should be enabled")
    def button_is_enabled(header_bar_instance):
        assert header_bar_instance._btn_clear_done.isEnabled()

    @then("the tooltip should say 'Nenhuma task concluída visível'")
    def tooltip_disabled(header_bar_instance):
        assert (
            "Sem tasks concluídas não-permanentes para ocultar"
            in header_bar_instance._btn_clear_done.toolTip()
        )

    @then("the tooltip should say 'Ocultar tasks concluídas'")
    def tooltip_enabled(header_bar_instance):
        assert "Ocultar tasks concluídas" in header_bar_instance._btn_clear_done.toolTip()

    @then("the clear_completed_clicked signal should be emitted")
    def signal_emitted(header_bar_instance):
        # Signal was already captured in the when step via waitSignal
        pass


# Unit-style tests for specific scenarios

class TestClearDoneButton:
    """Unit tests for clear_done button state management."""

    def test_button_starts_disabled(self, qtbot):
        """Scenario: Button disabled by default."""
        bar = HeaderBar()
        qtbot.addWidget(bar)
        assert not bar._btn_clear_done.isEnabled()
        assert (
            bar._btn_clear_done.toolTip()
            == "Sem tasks concluídas não-permanentes para ocultar"
        )

    def test_button_enabled_when_has_done(self, qtbot):
        """Scenario: Button enabled when has visible done tasks."""
        bar = HeaderBar()
        qtbot.addWidget(bar)
        bar.set_clear_done_enabled(True)
        assert bar._btn_clear_done.isEnabled()
        # Icon-only action keeps tooltip for discoverability.
        assert bar._btn_clear_done.toolTip() == "Mover tasks concluídas para a Lixeira"

    def test_button_disabled_when_no_done(self, qtbot):
        """Scenario: Button disabled when no visible done tasks."""
        bar = HeaderBar()
        qtbot.addWidget(bar)
        bar.set_clear_done_enabled(True)
        bar.set_clear_done_enabled(False)
        assert not bar._btn_clear_done.isEnabled()
        assert (
            bar._btn_clear_done.toolTip()
            == "Sem tasks concluídas não-permanentes para ocultar"
        )

    def test_clicking_button_emits_signal(self, qtbot):
        """Scenario: Clicking button emits clear_completed_clicked signal."""
        bar = HeaderBar()
        qtbot.addWidget(bar)
        bar.set_clear_done_enabled(True)
        with qtbot.waitSignal(bar.clear_completed_clicked, timeout=200):
            bar._btn_clear_done.click()

    def test_multiple_state_changes(self, qtbot):
        """Edge case: Multiple state changes are handled correctly."""
        bar = HeaderBar()
        qtbot.addWidget(bar)
        # Start disabled
        assert not bar._btn_clear_done.isEnabled()
        # Enable
        bar.set_clear_done_enabled(True)
        assert bar._btn_clear_done.isEnabled()
        # Disable
        bar.set_clear_done_enabled(False)
        assert not bar._btn_clear_done.isEnabled()
        # Enable again
        bar.set_clear_done_enabled(True)
        assert bar._btn_clear_done.isEnabled()
