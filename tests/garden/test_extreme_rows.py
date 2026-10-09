from __future__ import annotations

from borges.analysis.models import AnalysisPlan, ColumnProfile, DatasetProfile
from borges.garden.extreme_rows import extreme_rows_note
from borges.garden.flips import changes_for
from borges.garden.models import Flip
from tests.garden.synthetic import RULE, option, result, step_of


def plan(maximum: float = 61000.0) -> AnalysisPlan:
    summary = {"mean": 12.29, "std": 635.6, "min": 0.0, "p50": 0.0, "max": maximum}
    column = ColumnProfile(name="revenue", dtype="float", n_missing=0, n_unique=9, summary=summary)
    winsorize = step_of(
        "winsorize_revenue",
        "transform",
        option("w99", True),
        option("raw", label="No winsorizing"),
    )
    return AnalysisPlan(
        question="q",
        estimand="e",
        decision_rule=RULE,
        dataset=DatasetProfile(name="d", n_rows=100, columns=[column]),
        steps=[winsorize, step_of("estimate", "model", option("ttest", True))],
    )


def flip_of(target: AnalysisPlan, n_after: int = 100) -> Flip:
    return Flip(
        universe_id="u",
        changes=changes_for(target, {"winsorize_revenue": "raw"}),
        baseline_result=result(0.656, p=0.002),
        flipped_result=result(10.44, half=13.0, p=0.12, n=n_after),
        baseline_verdict="SHIP",
        flipped_verdict="DON'T SHIP",
        kind="significance",
    )


def test_a_winsorizing_flip_says_the_extreme_values_carry_it() -> None:
    target = plan()
    note = extreme_rows_note(target, flip_of(target))
    assert note is not None
    assert "extreme values of revenue" in note
    assert "the median is 0 but the maximum is 61,000" in note
    assert "0.656 (p=0.002)" in note and "10.4 (p=0.12, interval -2.56 to 23.4)" in note
    assert "too noisy to be significant" in note


def test_a_trimming_flip_that_moves_rows_says_how_many() -> None:
    target = plan()
    note = extreme_rows_note(target, flip_of(target, n_after=97))
    assert note is not None and "from 100 to 97 rows" in note


def test_a_flat_column_or_another_step_gets_no_note() -> None:
    flat = plan(maximum=30.0)
    assert extreme_rows_note(flat, flip_of(flat)) is None
    other = plan()
    flip = flip_of(other).model_copy(update={"changes": []})
    assert extreme_rows_note(other, flip) is None
    assert extreme_rows_note(other, None) is None
