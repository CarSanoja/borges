from __future__ import annotations

from borges.analysis.model_spec.validate_named_exposure import (
    named_exposure_problems,
    named_exposures,
)
from tests.analysis.model_spec.data import make_spec

COLUMNS = ["y", "campaign", "contact", "job", "redCards", "player_skintone", "games"]
BANK = (
    "Estimate a logistic regression model with dependent variable 'y' and independent variables: "
    "'campaign' (linear), plus covariates: job, contact. Return exp(coefficient of 'campaign')."
)


def test_the_column_an_option_names_as_its_exposure_is_found() -> None:
    assert named_exposures(BANK, COLUMNS) == ["campaign"]
    text = "Fit NegativeBinomial regression of redCards on player_skintone and covariates"
    assert named_exposures(text, COLUMNS) == ["player_skintone"]


def test_a_spec_that_reports_another_column_is_refused() -> None:
    spec = make_spec("logit", outcome="y", exposure="contact", covariates=["campaign", "job"])
    [problem] = named_exposure_problems(spec, BANK, COLUMNS)
    assert "'campaign'" in problem and "'contact'" in problem


def test_a_spec_on_the_named_exposure_passes() -> None:
    spec = make_spec("logit", outcome="y", exposure="campaign", covariates=["contact", "job"])
    assert named_exposure_problems(spec, BANK, COLUMNS) == []


def test_an_option_that_names_no_exposure_is_not_checked() -> None:
    spec = make_spec("ols", outcome="y", exposure="contact")
    assert named_exposure_problems(spec, "OLS with robust errors.", COLUMNS) == []
