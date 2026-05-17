# @tdd-locked: do not edit without /tdd:unlock
# Suite: unit | Module: module-0-foundations | Task: TASK-2
# TIDs: TID-0-2-001, TID-0-2-002, TID-0-2-003, TID-0-2-004, TID-0-2-005, TID-0-2-006, TID-0-2-007, TID-0-2-008, TID-0-2-009
import pytest

from task_manager_desktop.core.models import (
    Color,
    PROJETO_DEFAULT,
    Sector,
    Status,
    TaskType,
    normalize_projeto,
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

    def test_tasktype_enum_tem_exatamente_2_membros(self):
        values = {t.value for t in TaskType}
        assert values == {"online", "offline"}
        assert len(TaskType) == 2


class TestSectorEnum:
    """TID-0-2-005 | covers: TASK-2/ST001 + OVERVIEW Contratos + ARCHITECTURE | suite: unit"""

    def test_sector_enum_tem_6_zonas_canonicas(self):
        # compute_sector mapeia (status x has_open_deps) -> 4 combinacoes distintas;
        # Sector define as zonas: ACTIVE, WAITING, BLOCKED, DONE
        expected = {"ACTIVE", "WAITING", "BLOCKED", "DONE"}
        assert {s.name for s in Sector} == expected


class TestColorEnum:
    """TID-0-2-006 | covers: TASK-2/ST001 + OVERVIEW Contratos | suite: unit"""

    def test_color_enum_cardinalidade_igual_a_sector(self):
        assert len(Color) == len(Sector)


class TestNormalizeProjetoNone:
    """TID-0-2-007 | covers: TASK-2/ST001 BDD#5 | suite: unit | classification: EDGE"""

    def test_normalize_projeto_none_retorna_projeto_default(self):
        assert normalize_projeto(None) == PROJETO_DEFAULT
        assert PROJETO_DEFAULT == "outros"


class TestNormalizeProjetoEspacos:
    """TID-0-2-008 | covers: TASK-2/ST001 BDD#6 | suite: unit | classification: EDGE"""

    def test_normalize_projeto_espacos_retorna_projeto_default(self):
        assert normalize_projeto("   ") == PROJETO_DEFAULT


class TestNormalizeProjetoVerbatim:
    """TID-0-2-009 | covers: TASK-2/ST001 BDD#7 | suite: unit"""

    def test_normalize_projeto_preserva_valor_verbatim(self):
        assert normalize_projeto("alpha") == "alpha"
        assert normalize_projeto("Alpha") == "Alpha"
