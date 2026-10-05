from __future__ import annotations

from borges.analysis.model_spec.produced_outcome import with_produced_outcome
from tests.analysis.model_spec.data import make_spec

TEXT = "Regress outcome on masfem and covariates in ctx['covariates'] using statsmodels.OLS."


def test_the_hurricanes_transformed_outcome_is_modelled() -> None:
    spec = make_spec("ols", outcome="alldeaths", exposure="masfem")
    assert with_produced_outcome(spec, TEXT, ["outcome"]).outcome == "outcome"


def test_a_named_column_no_step_produces_is_left_alone() -> None:
    spec = make_spec("ols", outcome="alldeaths", exposure="masfem")
    assert with_produced_outcome(spec, TEXT, []).outcome == "alldeaths"
    formula = "Fit alldeaths ~ masfem with Poisson."
    assert with_produced_outcome(spec, formula, ["outcome"]).outcome == "alldeaths"


def test_a_standardised_outcome_stays_standardised() -> None:
    spec = make_spec("ols", outcome="alldeaths", exposure="masfem", standardize=["alldeaths"])
    assert with_produced_outcome(spec, TEXT, ["outcome"]).standardize == ["outcome"]


def test_an_outcome_assigned_to_y_from_a_produced_column_is_modelled() -> None:
    spec = make_spec("ols", outcome="alldeaths", exposure="masfem")
    text = "y = df['outcome']; X = df[ctx['covariates'] + ['masfem']]; sm.OLS(y, X).fit()"
    assert with_produced_outcome(spec, text, ["outcome"]).outcome == "outcome"
    assert with_produced_outcome(spec, text.replace("y =", "endog ="), ["outcome"]).outcome == (
        "outcome"
    )
    assert with_produced_outcome(spec, text, []).outcome == "alldeaths"
