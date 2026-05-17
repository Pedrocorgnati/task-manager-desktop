# @tdd-locked: do not edit without /tdd:unlock
# Suite: contract | Module: module-0-foundations | Task: TASK-2
# TIDs: TID-0-2-027
import re
from pathlib import Path

import pytest


class TestCoreLayeringNoPySide6:
    """TID-0-2-027 | covers: OVERVIEW DoD, AC-T-004, ARCHITECTURE D-001 | suite: contract

    Gate de layering canonico: nenhum arquivo em task_manager_desktop/core/
    pode importar PySide6 (separacao core/ vs ui/).
    """

    def test_core_does_not_import_pyside6(self):
        core_dir = Path(__file__).parents[4] / "task_manager_desktop" / "core"
        pattern = re.compile(r"(from PySide6|import PySide6)")
        violations = []
        for py_file in core_dir.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    violations.append(f"{py_file.name}:{lineno}: {line.strip()}")
        assert violations == [], (
            "core/ nao pode importar PySide6 (ARCHITECTURE D-001):\n"
            + "\n".join(violations)
        )
