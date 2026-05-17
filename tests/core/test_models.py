from dataclasses import fields

import pytest

from task_manager_desktop.core.models import (
    PROJETO_DEFAULT,
    Color,
    Sector,
    Status,
    Task,
    TaskType,
    normalize_projeto,
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

    def test_tasktype_has_exactly_2_values_with_online_default(self):
        assert {t.value for t in TaskType} == {"online", "offline"}
        assert Task(id="abc", title="t").type == TaskType.ONLINE

    def test_sector_label_pt(self):
        assert Sector(1).label_pt() == "Em andamento"
        assert Sector(2).label_pt() == "A fazer"
        assert Sector(3).label_pt() == "Bloqueada"
        assert Sector(4).label_pt() == "Concluída"

    def test_sector_has_exactly_4_values(self):
        assert len(list(Sector)) == 4

    def test_color_has_exactly_4_values(self):
        assert {c.value for c in Color} == {"green", "yellow", "gray", "neutral"}


class TestNormalizeProjeto:
    @pytest.mark.parametrize("value", [None, "", "   ", "\t\n"])
    def test_empty_or_none_returns_sentinel(self, value):
        assert normalize_projeto(value) == PROJETO_DEFAULT
        assert PROJETO_DEFAULT == "outros"

    def test_preserves_non_empty_verbatim(self):
        assert normalize_projeto("systemforge") == "systemforge"
        assert normalize_projeto("  trimmed  ") == "  trimmed  "


class TestTaskDataclass:
    def test_has_11_fields(self):
        assert len(fields(Task)) == 11

    def test_defaults_are_sane(self):
        t = Task(id="abc", title="x")
        assert t.deps == []
        assert t.projeto == PROJETO_DEFAULT
        assert t.type == TaskType.ONLINE
        assert t.completed_at is None
        assert t.hidden_at is None
