# @tdd-unlocked: feature favorito/permanente (source.md §3.2) adicionou o setor
#   PERMANENT e desacoplou Color de Sector — contrato canonico atualizado.
# Suite: unit | Module: module-0-foundations | Task: TASK-2
# TIDs: TID-0-2-001, TID-0-2-002, TID-0-2-003, TID-0-2-004, TID-0-2-005, TID-0-2-006, TID-0-2-007, TID-0-2-008, TID-0-2-009
import pytest

from task_manager_desktop.core.models import (
    Color,
    Sector,
    Status,
    TaskType,
    parse_deps,
)


class TestParseDepsCSV:
    """TID-0-2-001 | covers: TASK-2/ST001 BDD#1 | suite: unit"""

    def test_parse_deps_split_csv_com_espacos(self):
        assert parse_deps("a, b, c") == ["a", "b", "c"]


class TestParseDepsIgnoraVazios:
    """TID-0-2-002 | covers: TASK-2/ST001 BDD#2 | suite: unit | classification: EDGE"""

    def test_parse_deps_ignora_vazios(self):
        assert parse_deps(",,a,") == ["a"]


class TestStatusEnum:
    """TID-0-2-003 | covers: TASK-2/ST001 BDD#3 | suite: unit"""

    def test_status_enum_tem_exatamente_3_membros(self):
        values = {s.value for s in Status}
        assert values == {"pending", "in_progress", "done"}
        assert len(Status) == 3


class TestTaskTypeEnum:
    """TID-0-2-004 | covers: TASK-2/ST001 BDD#4 | suite: unit"""

    def test_tasktype_enum_tem_exatamente_3_membros(self):
        values = {t.value for t in TaskType}
        assert values == {"agent", "dev", "human"}
        assert len(TaskType) == 3


class TestSectorEnum:
    """TID-0-2-005 | covers: TASK-2/ST001 + OVERVIEW Contratos + ARCHITECTURE | suite: unit"""

    def test_sector_enum_tem_6_zonas_canonicas(self):
        # Sector define as zonas: ACTIVE, WAITING, BLOCKED, DONE, PERMANENT.
        # PERMANENT (source.md §3.2) e o 5o setor introduzido pela feature
        # favorito/permanente; EM_PREPARACAO e o setor manual "Em preparação".
        expected = {
            "ACTIVE", "WAITING", "BLOCKED", "DONE", "PERMANENT", "EM_PREPARACAO"
        }
        assert {s.name for s in Sector} == expected
        assert len(Sector) == 6


class TestColorEnum:
    """TID-0-2-006 | covers: TASK-2/ST001 + OVERVIEW Contratos | suite: unit"""

    def test_color_enum_tem_4_membros_base(self):
        # A feature favorito/permanente desacoplou Color de Sector: compute_sector
        # retorna tuple[Sector, str] e o setor PERMANENT usa um accent hex dedicado
        # (PERMANENT_ACCENT), nao um membro de Color. Color mantem as 4 cores base.
        assert {c.name for c in Color} == {"GREEN", "YELLOW", "GRAY", "NEUTRAL"}
        assert len(Color) == 4


