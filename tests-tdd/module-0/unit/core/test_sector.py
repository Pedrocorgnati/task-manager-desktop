# @tdd-locked: do not edit without /tdd:unlock
# Suite: unit | Module: module-0-foundations | Task: TASK-2
# TIDs: TID-0-2-010, TID-0-2-011
import pytest

from task_manager_desktop.core.models import Color, Sector, Status, Task
from task_manager_desktop.core.sector import compute_sector, count_open_deps


class TestComputeSectorParametrizado:
    """TID-0-2-010 | covers: TASK-2/ST002 + OVERVIEW Contratos + US-005 | suite: unit"""

    @pytest.mark.parametrize("status,has_open_deps,expected_sector,expected_color", [
        (Status.DONE,        False, Sector.DONE,    Color.NEUTRAL),
        (Status.DONE,        True,  Sector.DONE,    Color.NEUTRAL),
        (Status.IN_PROGRESS, True,  Sector.ACTIVE,  Color.GRAY),
        (Status.IN_PROGRESS, False, Sector.ACTIVE,  Color.GREEN),
        (Status.PENDING,     True,  Sector.BLOCKED, Color.GRAY),
        (Status.PENDING,     False, Sector.WAITING, Color.YELLOW),
    ])
    def test_compute_sector_6_combinacoes_status_has_open_deps(
        self, status, has_open_deps, expected_sector, expected_color
    ):
        sector, color = compute_sector(status, has_open_deps)
        assert sector == expected_sector
        assert color == expected_color


class TestCountOpenDepsIgnoraIdsNaoEncontrados:
    """TID-0-2-011 | covers: TASK-2/ST002 BDD#1 + US-001 cen.4 | suite: unit | classification: EDGE"""

    def test_count_open_deps_ignora_ids_nao_encontrados_silenciosamente(self):
        all_tasks: dict[str, Task] = {}
        result = count_open_deps(["x", "y"], all_tasks)
        assert result == 0
