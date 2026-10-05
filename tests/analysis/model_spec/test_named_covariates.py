from __future__ import annotations

from borges.analysis.model_spec.named_covariates import with_labelled_effects, with_named_covariates
from borges.analysis.model_spec.schema import ModelSpecOutput
from tests.analysis.model_spec.data import make_spec

COLUMNS = ["redCards", "dark_skin", "games", "leagueCountry", "position", "refNum", "meanIAT"]
MINIMAL = (
    "Fit Poisson regression with log(games) as offset, predictors dark_skin, leagueCountry "
    "(categorical, drop_first=True), position (categorical, drop_first=True); use statsmodels.GLM "
    "with family=Poisson(); cluster on refNum; return the coefficient for dark_skin."
)


def test_predictors_the_spec_left_out_are_added_back() -> None:
    spec = make_spec("poisson", outcome="redCards", exposure="dark_skin", covariates=[])
    fixed = with_named_covariates(spec, MINIMAL, COLUMNS, None)
    assert fixed.covariates == ["leagueCountry", "position"]


def test_an_option_without_other_predictors_is_left_alone() -> None:
    spec = make_spec("poisson", outcome="redCards", exposure="dark_skin", covariates=[])
    text = "Fit Poisson with predictor dark_skin, no other covariates; use statsmodels.GLM."
    assert with_named_covariates(spec, text, COLUMNS, None).covariates == []
    listed = make_spec("poisson", outcome="redCards", exposure="dark_skin", covariates=["meanIAT"])
    fixed = with_named_covariates(listed, MINIMAL.replace("position", "meanIAT"), COLUMNS, None)
    assert fixed.covariates == ["meanIAT", "leagueCountry"]


def test_a_column_the_label_names_as_fixed_effects_is_added() -> None:
    spec = ModelSpecOutput.model_validate(
        {
            "supported": True,
            "family": "logit",
            "outcome": "y",
            "exposure": "campaign",
            "covariates_from_ctx": True,
        }
    )
    columns = ["y", "campaign", "month", "job"]
    found = with_labelled_effects(spec, "Logistic regression with month fixed effects", columns)
    assert found.covariates == ["month"]
    assert with_labelled_effects(spec, "Logistic regression", columns).covariates == []
