from __future__ import annotations

from borges.analysis.models import StepTrace
from borges.garden.filtered_rows import filtered_rows_caveats
from tests.garden.synthetic import garden_of, option, plan_of, result, step_of, universe


def audit_plan():
    return plan_of(
        step_of("filter", "filter", option("drop_missing", True)),
        step_of("model", "model", option("logit", True)),
    )


def traces(kept: int) -> list[StepTrace]:
    return [
        StepTrace(step_id="filter", option_id="x", rows_before=100, rows_after=kept),
        StepTrace(step_id="model", option_id="x", rows_before=kept, rows_after=kept),
    ]


def test_a_filter_that_drops_a_tenth_of_the_rows_is_named() -> None:
    plan = audit_plan()
    baseline = universe(plan, {}, result(-0.005, n=87), traces=traces(87))
    [note] = filtered_rows_caveats(plan, garden_of(plan, baseline))
    assert note.startswith("The original analysis's model receives 87 of the 100 uploaded rows")
    assert "(13% left out): 'Step filter' drops 13" in note


def test_a_filter_that_keeps_almost_every_row_gives_no_note() -> None:
    plan = audit_plan()
    baseline = universe(plan, {}, result(-0.005, n=97), traces=traces(97))
    assert filtered_rows_caveats(plan, garden_of(plan, baseline)) == []
