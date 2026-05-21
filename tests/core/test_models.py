from dataclasses import fields

import pytest

from task_manager_desktop.core.models import (
    Color,
    Sector,
    Status,
    Task,
    TaskType,
    parse_deps,
)


class TestParseDeps:
    def test_splits_csv_with_spaces(self):
        assert parse_deps("abc, xyz, k9p") == ["abc", "xyz", "k9p"]

    def test_ignores_empty_entries(self):
        assert parse_deps("abc,,xyz") == ["abc", "xyz"]

    def test_empty_string_returns_empty_list(self):
        assert parse_deps("") == []

    def test_only_whitespace_returns_empty_list(self):
        assert parse_deps("   ,  ,") == []


class TestEnums:
    def test_status_has_exactly_3_values(self):
        assert {s.value for s in Status} == {"pending", "in_progress", "done"}

    def test_tasktype_has_expected_values_with_agent_default(self):
        assert {t.value for t in TaskType} == {"agent", "dev", "human"}
        assert Task(id="abc", title="t").type == TaskType.AGENT

    def test_sector_label_pt(self):
        assert Sector(1).label_pt() == "Em andamento"
        assert Sector(2).label_pt() == "A fazer"
        assert Sector(3).label_pt() == "Bloqueada"
        assert Sector(4).label_pt() == "Concluída"
        assert Sector(5).label_pt() == "Permanentes"

    def test_sector_has_exactly_5_values(self):
        assert len(list(Sector)) == 5

    def test_color_has_exactly_4_values(self):
        assert {c.value for c in Color} == {"green", "yellow", "gray", "neutral"}


class TestTaskDataclass:
    def test_has_12_fields(self):
        assert len(fields(Task)) == 12

    def test_defaults_are_sane(self):
        t = Task(id="abc", title="x")
        assert t.deps == []
        assert t.type == TaskType.AGENT
        assert t.completed_at is None
        assert t.hidden_at is None
