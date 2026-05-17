# @tdd-locked: do not edit without /tdd:unlock
# Suite: contract | Module: module-0-foundations | Task: TASK-3
# TIDs: TID-0-3-022
import re
from pathlib import Path

import pytest


class TestUiNoHardcodedHexColors:
    """TID-0-3-022 | covers: OVERVIEW DoD Qualidade, OVERVIEW Risco hardcode hex
    | suite: contract

    Gate canonico: nenhum arquivo em task_manager_desktop/ui/*.py pode ter
    cores hex literais (#RRGGBB). Todas devem vir de ui/theme.py.
    """

    def test_ui_modules_have_no_hex_literals(self):
        ui_dir = Path(__file__).parents[4] / "task_manager_desktop" / "ui"
        pattern = re.compile(r'#[0-9a-fA-F]{6}')
        violations = []
        for py_file in ui_dir.glob("*.py"):
            if py_file.name == "theme.py":
                continue
            text = py_file.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    violations.append(f"{py_file.name}:{lineno}: {line.strip()}")
        assert violations == [], (
            "ui/ nao pode ter hex literals (use theme.PALETTE):\n"
            + "\n".join(violations)
        )
