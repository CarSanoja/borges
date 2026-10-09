from __future__ import annotations

from borges.garden.contaminated_options import contaminated_options
from borges.garden.flips import contaminated_flips
from tests.garden.synthetic import garden_of, option, plan_of, result, step_of, trace, universe

RATIONALE = "Missing country may indicate data quality issues or bots"


def country_plan(notes: dict[str, str] | None = None):
    drop = option("drop", True, code="df[df.country.notna()]", label="Exclude missing country")
    drop.rationale = RATIONALE
    return plan_of(
        step_of("rows", "filter", drop, option("keep", label="Keep missing country")),
        step_of("model", "model", option("ols", True), option("logit")),
        notes=notes,
    )


def garden_for(plan):
    return garden_of(
        plan,
        universe(plan, {}, result(0.1, p=0.4), traces=[trace("rows", rows_after=900)]),
        universe(plan, {"rows": "keep"}, result(1.0), traces=[trace("rows", rows_after=1000)]),
    )


def test_the_planners_own_rationale_never_marks_rows_invalid() -> None:
    plan = country_plan()
    garden = garden_for(plan)
    assert contaminated_options(plan, garden) == []
    assert contaminated_flips(plan, garden) == []


def test_a_note_the_user_wrote_flags_the_rows_and_the_plan_is_quoted_as_the_plan() -> None:
    plan = country_plan({"country": "country of the visitor; missing means a bot or test session"})
    garden = garden_for(plan)
    [found] = contaminated_options(plan, garden)
    assert "the column notes mark as invalid (bot, test)" in found.reason
    assert f"the plan's default drops these rows because {RATIONALE}" in found.reason
    [flip] = contaminated_flips(plan, garden)
    assert "the plan's default drops these rows because" in (flip.contamination_reason or "")


def test_the_question_the_user_asked_can_name_the_invalid_rows() -> None:
    plan = country_plan()
    plan.question = "Does the new page lift conversion once bots are removed?"
    [found] = contaminated_options(plan, garden_for(plan))
    assert "(bots)" in found.reason
