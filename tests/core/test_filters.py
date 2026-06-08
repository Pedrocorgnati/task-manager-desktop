from __future__ import annotations

from task_manager_desktop.core.filters import (
    card_matches_subtasks,
    is_active,
)
from task_manager_desktop.core.models import TaskType


def test_is_active_detects_partial_type_filter():
    assert is_active(task_types={"human", "agent"})
    assert is_active(task_types=set())


def test_is_active_false_when_all_types_selected():
    assert not is_active()
    assert not is_active(task_types={t.value for t in TaskType})


def test_card_matches_when_has_subtask_of_selected_type():
    assert card_matches_subtasks({"agent"}, task_types={"agent"})
    assert card_matches_subtasks({"dev", "human"}, task_types={"human"})
    # aceita TaskType tambem
    assert card_matches_subtasks([TaskType.DEV], task_types={TaskType.DEV})


def test_card_does_not_match_when_no_subtask_of_selected_type():
    assert not card_matches_subtasks({"dev"}, task_types={"agent"})
    # card sem subtasks nunca casa sob filtro ativo
    assert not card_matches_subtasks(set(), task_types={"agent"})
    # nenhum tipo selecionado -> nada casa
    assert not card_matches_subtasks({"agent", "dev"}, task_types=set())
