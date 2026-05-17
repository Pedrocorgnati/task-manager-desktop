# @tdd-locked: do not edit without /tdd:unlock
# Suite: contract | Module: module-0-foundations | Task: TASK-2
# TIDs: TID-0-2-024
import pytest


class TestCorePackagePublicImports:
    """TID-0-2-024 | covers: OVERVIEW Contratos | suite: contract

    Contrato: from task_manager_desktop.core import Task, Status, Sector, Color,
    TaskType, PROJETO_DEFAULT, parse_deps, normalize_projeto.
    """

    def test_core_package_exposes_canonical_symbols(self):
        import task_manager_desktop.core as core

        expected = {
            "Task", "Status", "Sector", "Color", "TaskType",
            "PROJETO_DEFAULT", "parse_deps", "normalize_projeto",
        }
        for sym in expected:
            assert hasattr(core, sym), f"Simbolo ausente em core.__init__: {sym}"

        assert hasattr(core, "__all__"), "core.__all__ deve existir"
        assert expected.issubset(set(core.__all__)), (
            f"Simbolos faltando em __all__: {expected - set(core.__all__)}"
        )
