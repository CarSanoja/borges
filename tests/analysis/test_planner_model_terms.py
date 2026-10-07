from __future__ import annotations

from borges.analysis.models import ColumnProfile, DatasetProfile
from borges.analysis.planner_model_terms import built_terms, model_terms_shortfall
from borges.analysis.schemas import PlannedOption, PlannedStep

PROFILE = DatasetProfile(
    name="vote",
    n_rows=502,
    columns=[
        ColumnProfile(name=n, dtype="float64", n_missing=0, n_unique=10)
        for n in ("Vote", "Relationship", "variant")
    ],
)
RUN_39 = (
    "If ctx['covariates'] is empty, formula = 'Vote ~ high + committed + high:committed'; "
    "where high = (cycle_day >= 7) & (cycle_day <= 14); fit statsmodels.Logit with method='bfgs'"
)


def steps(model_spec: str) -> list[PlannedStep]:
    def option(spec: str) -> list[PlannedOption]:
        return [PlannedOption(id="a", label="a", rationale="r", spec=spec, is_default=True)]

    return [
        PlannedStep(
            id="days",
            title="d",
            kind="feature",
            description="d",
            options=option("cycle_day = 28 - days"),
            produces=["cycle_day", "committed"],
        ),
        PlannedStep(
            id="model", title="m", kind="model", description="d", options=option(model_spec)
        ),
    ]


def test_a_model_that_builds_its_exposure_from_a_range_goes_back_to_the_planner() -> None:
    """fertility_vote on 7 October, run 39: every model option took cycle_day as the exposure."""
    found = model_terms_shortfall(steps(RUN_39), PROFILE)
    assert found is not None and "model.a: high" in found


def test_a_level_of_a_column_or_a_term_built_earlier_is_left_to_the_model() -> None:
    level = "treatment = (variant == 'B').astype(int). Fit Vote ~ treatment; p <= 0.05 if needed"
    assert model_terms_shortfall(steps(level), PROFILE) is None
    assert built_terms("Vote ~ cycle_day; cycle_day = x > 3", {"cycle_day"}) == []
    assert built_terms("formula = 'Vote ~ C(variant, Treatment(reference=\"a\"))'\n", set()) == []
