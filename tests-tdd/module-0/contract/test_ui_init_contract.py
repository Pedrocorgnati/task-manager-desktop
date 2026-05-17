# @tdd-locked: do not edit without /tdd:unlock
# Suite: contract | Module: module-0-foundations | Task: TASK-3
# TIDs: TID-0-3-021
import pytest


class TestUiPackagePublicImports:
    """TID-0-3-021 | covers: OVERVIEW Contratos | suite: contract

    Contrato: from task_manager_desktop.ui import ToastWidget, ErrorDialog,
    EmptyStateLabel, MainWindowShell.
    """

    def test_ui_package_exposes_canonical_symbols(self):
        import task_manager_desktop.ui as ui

        expected = {"ToastWidget", "ErrorDialog", "EmptyStateLabel", "MainWindowShell"}
        for sym in expected:
            assert hasattr(ui, sym), f"Simbolo ausente em ui.__init__: {sym}"

        assert hasattr(ui, "__all__"), "ui.__all__ deve existir"
        assert expected.issubset(set(ui.__all__)), (
            f"Simbolos faltando em __all__: {expected - set(ui.__all__)}"
        )
