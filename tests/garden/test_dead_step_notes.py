from __future__ import annotations

from borges.garden.models import NoopOption
from borges.garden.report_duplicate_notes import dead_step_notes
from tests.garden.synthetic import option, plan_of, step_of


def noop(step_id: str, option_id: str) -> NoopOption:
    return NoopOption(step_id=step_id, option_id=option_id, label=option_id, reason="same")


def test_a_dead_model_step_is_described_as_equal_results() -> None:
    plan = plan_of(
        step_of("cov", "feature", option("none", True), option("age")),
        step_of("fit", "model", option("cluster", True), option("hc2")),
    )
    [note] = dead_step_notes(plan, [noop("fit", "hc2")])
    assert "The decision 'Step fit' had no effect on the result" in note
    assert "the alternatives give the same estimate and interval as the default" in note
    assert "ignores" not in note


def test_a_dead_covariate_step_says_the_model_ignores_it() -> None:
    plan = plan_of(
        step_of("cov", "feature", option("none", True), option("age")),
        step_of("fit", "model", option("cluster", True), option("hc2")),
    )
    [note] = dead_step_notes(plan, [noop("cov", "age")])
    assert "covariate decision 'Step cov'" in note and "ignores or always includes" in note
