from __future__ import annotations

from borges.analysis.models import ColumnProfile, DatasetProfile, StepTrace
from borges.garden.likelihood_question import likelihood_caveats
from borges.garden.models import Garden, Universe
from tests.garden.fakes import make_plan

AFFAIRS = ColumnProfile(
    name="affairs", dtype="float64", n_missing=0, n_unique=77, summary={"min": 0.0, "max": 57.6}
)
HAD = ColumnProfile(name="had_affair", dtype="int64", n_missing=0, n_unique=2)
SCORE = ColumnProfile(
    name="score", dtype="float64", n_missing=0, n_unique=400, summary={"min": 12.0}
)


def plan_for(question: str):
    plan = make_plan()
    dataset = DatasetProfile(name="d", n_rows=601, columns=[AFFAIRS, HAD, SCORE])
    return plan.model_copy(update={"question": question, "dataset": dataset})


def garden_on(outcome: str) -> Garden:
    trace = StepTrace(
        step_id="m",
        option_id="o",
        rows_before=601,
        rows_after=601,
        design={"outcome": outcome, "names": ["const", "relig"]},
    )
    garden = Garden()
    garden.add(Universe(id="u0", choices={}, kind="baseline", traces=[trace]))
    garden.baseline_id = "u0"
    return garden


def test_a_likelihood_question_on_a_count_says_what_was_measured() -> None:
    plan = plan_for("Are more religious women less likely to have affairs?")
    [caveat] = likelihood_caveats(plan, garden_on("affairs"))
    assert '("likely")' in caveat
    assert "models affairs, which takes 77 values" in caveat
    assert "(for example affairs > 0)" in caveat


def test_a_likelihood_question_on_a_yes_no_outcome_needs_no_caveat() -> None:
    plan = plan_for("Are more religious women less likely to have affairs?")
    assert likelihood_caveats(plan, garden_on("had_affair")) == []


def test_a_question_about_an_amount_needs_no_caveat() -> None:
    plan = plan_for("Does tutoring raise math scores?")
    assert likelihood_caveats(plan, garden_on("score")) == []


def test_a_spanish_question_and_an_outcome_without_zero() -> None:
    plan = plan_for("¿Es menos probable que aprueben los alumnos con tutoría?")
    [caveat] = likelihood_caveats(plan, garden_on("score"))
    assert '("probable")' in caveat
    assert "(a yes/no version of score)" in caveat


def test_an_outcome_the_profile_does_not_know_is_left_alone() -> None:
    plan = plan_for("Are they less likely to churn?")
    assert likelihood_caveats(plan, garden_on("derived_flag")) == []
    assert likelihood_caveats(plan, Garden()) == []
