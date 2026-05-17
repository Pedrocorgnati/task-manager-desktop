import pytest

from task_manager_desktop.core.models import Color, Sector, Status, Task
from task_manager_desktop.core.sector import compute_sector, count_open_deps


@pytest.mark.parametrize("status,has_open,expected", [
    (Status.IN_PROGRESS, False, (Sector(1), Color.GREEN)),
    (Status.IN_PROGRESS, True,  (Sector(1), Color.GRAY)),
    (Status.PENDING,     False, (Sector(2), Color.YELLOW)),
    (Status.PENDING,     True,  (Sector(3), Color.GRAY)),
    (Status.DONE,        False, (Sector(4), Color.NEUTRAL)),
    (Status.DONE,        True,  (Sector(4), Color.NEUTRAL)),
])
def test_compute_sector_all_combinations(status, has_open, expected):
    assert compute_sector(status, has_open) == expected


def test_count_open_deps_ignores_unknown_ids():
    a = Task(id="a", title="A", status=Status.PENDING)
    all_tasks = {"a": a}
    assert count_open_deps(["a", "xyz999"], all_tasks) == 1


def test_count_open_deps_excludes_done():
    a = Task(id="a", title="A", status=Status.DONE)
    b = Task(id="b", title="B", status=Status.PENDING)
    assert count_open_deps(["a", "b"], {"a": a, "b": b}) == 1


def test_count_open_deps_empty_list():
    assert count_open_deps([], {}) == 0


def test_count_open_deps_all_done():
    a = Task(id="a", title="A", status=Status.DONE)
    b = Task(id="b", title="B", status=Status.DONE)
    assert count_open_deps(["a", "b"], {"a": a, "b": b}) == 0
