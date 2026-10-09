from __future__ import annotations

from borges.garden.duplicate_rows import duplicate_row_caveats
from tests.analysis.fakes import make_plan


def plan_with(n_rows: int, duplicates: int):
    plan = make_plan()
    plan.dataset = plan.dataset.model_copy(update={"n_rows": n_rows, "duplicate_rows": duplicates})
    return plan


def test_many_exact_copies_get_a_plain_caveat() -> None:
    [caveat] = duplicate_row_caveats(plan_with(20190, 11065))
    assert caveat.startswith("11,065 of 20,190 rows are exact copies of another row")


def test_a_few_stray_copies_get_no_caveat() -> None:
    assert duplicate_row_caveats(plan_with(10535, 6)) == []
    assert duplicate_row_caveats(plan_with(0, 0)) == []
