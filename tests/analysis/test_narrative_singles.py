from __future__ import annotations

from borges.analysis.narrative_singles import restate_single_counts
from borges.garden.models import Report
from tests.garden.synthetic import garden_of, option, plan_of, result, step_of, universe

PLAN = plan_of(
    step_of("rows", "filter", option("all", True), option("int"), option("both")),
    step_of("m", "model", option("ols", True), option("cl")),
)
TEXT = "Two other single-change universes also flipped the verdict: both, and both with cl."


def report() -> Report:
    return Report.model_validate(
        {
            "question": "q",
            "original_verdict": "SHIP",
            "original_result": result(0.5),
            "minimal_flip": None,
            "influences": [],
            "robustness": 0.8,
            "n_universes": 4,
            "n_flipped": 3,
        }
    )


def garden():
    return garden_of(
        PLAN,
        universe(PLAN, {}, result(0.5)),
        universe(PLAN, {"rows": "int"}, result(-0.1)),
        universe(PLAN, {"rows": "both"}, result(-0.1)),
        universe(PLAN, {"rows": "both", "m": "cl"}, result(-0.1)),
    )


def test_a_count_of_single_changes_the_garden_does_not_have_loses_its_number() -> None:
    assert restate_single_counts(report(), garden(), TEXT) == TEXT
    out = restate_single_counts(report(), garden(), "One other " + TEXT[10:])
    assert out.startswith("Other universes also flipped")
    assert restate_single_counts(report(), garden(), "Three " + TEXT[10:]).startswith(
        "Some universes"
    )
    assert restate_single_counts(report(), None, "Three " + TEXT[10:]).startswith("Three")
