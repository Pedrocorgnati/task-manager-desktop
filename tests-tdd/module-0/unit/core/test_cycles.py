# @tdd-locked: do not edit without /tdd:unlock
# Suite: unit | Module: module-0-foundations | Task: TASK-2
# TIDs: TID-0-2-015, TID-0-2-016, TID-0-2-017, TID-0-2-018
import pytest

from task_manager_desktop.core.cycles import resolve_cycles
from task_manager_desktop.core.models import Task


def _task(tid: str, deps: list[str]) -> Task:
    return Task(id=tid, title=tid, deps=deps)


class TestResolveCyclesDireto:
    """TID-0-2-015 | covers: TASK-2/ST004 BDD#1 + ARCHITECTURE D-006 | suite: unit"""

    def test_resolve_cycles_ciclo_direto_a_b(self):
        all_tasks = {
            "A": _task("A", ["B"]),
            "B": _task("B", ["A"]),
        }
        # Propor adicionar dep de A->B quando B ja depende de A: cria ciclo
        safe, desc = resolve_cycles("A", ["B"], all_tasks)
        assert safe == [], "dep ciclica deve ser removida"
        assert desc is not None, "deve descrever a substituicao"
        assert "B" in desc


class TestResolveCyclesCadeia:
    """TID-0-2-016 | covers: TASK-2/ST004 BDD#2 | suite: unit"""

    def test_resolve_cycles_quebra_cadeia_a_b_c_a(self):
        # A->B->C->A: ao propor dep A em C, cria ciclo
        all_tasks = {
            "A": _task("A", ["B"]),
            "B": _task("B", ["C"]),
            "C": _task("C", []),
        }
        safe, desc = resolve_cycles("C", ["A"], all_tasks)
        assert safe == [], "dep A em C fecha o ciclo C->A->B->C"
        assert desc is not None


class TestResolveCyclesIdNaoExistente:
    """TID-0-2-017 | covers: TASK-2/ST004 BDD#3 + US-001 cen.4 | suite: unit | classification: EDGE"""

    def test_resolve_cycles_ignora_id_nao_existente(self):
        all_tasks = {
            "A": _task("A", []),
        }
        safe, desc = resolve_cycles("A", ["XYZ"], all_tasks)
        assert safe == [], "dep com ID inexistente deve ser silenciosamente ignorada"
        assert desc is None


class TestResolveCyclesDepMaisRecentePrevalesce:
    """TID-0-2-018 | covers: TASK-2/ST004 regra D-006 | suite: unit"""

    def test_dep_mais_recente_prevalece_ao_quebrar_ciclo(self):
        # A depende de B. Propor deps [C, B] para A: C e nova, B criaria ciclo porque A ja e dep de B
        all_tasks = {
            "A": _task("A", []),
            "B": _task("B", ["A"]),
            "C": _task("C", []),
        }
        safe, desc = resolve_cycles("A", ["C", "B"], all_tasks)
        assert "C" in safe, "C e dep valida, deve sobreviver"
        assert "B" not in safe, "B criaria ciclo (B->A ja existe)"
        assert desc is not None
