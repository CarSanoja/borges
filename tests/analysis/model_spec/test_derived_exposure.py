from __future__ import annotations

from borges.analysis.model_spec.derived_exposure import derived_exposure
from tests.analysis.model_spec.data import make_spec
from tests.analysis.model_spec.test_validate_exposure import AVAILABLE, PROFILE

SPEC_TEXT = (
    "Create treatment = (variant == 'treatment').astype(int); regress converted on treatment "
    "with HC1 standard errors."
)


def test_an_indicator_built_from_a_text_column_becomes_that_column_and_level() -> None:
    spec = make_spec("logit", outcome="y_bin", exposure="treatment", report="marginal_effect")
    fixed = derived_exposure(spec, SPEC_TEXT, AVAILABLE, PROFILE)
    assert fixed.exposure == "variant" and fixed.exposure_level == "treatment"


def test_without_a_stated_comparison_the_level_is_found_among_the_text_columns() -> None:
    spec = make_spec("ols", outcome="y_cont", exposure="treatment", standardize=["treatment"])
    fixed = derived_exposure(spec, "OLS of y on the treatment dummy", AVAILABLE, PROFILE)
    assert (fixed.exposure, fixed.exposure_level) == ("variant", "treatment")
    assert fixed.standardize == []


def test_an_available_exposure_or_an_ambiguous_one_is_left_alone() -> None:
    present = make_spec("ols", outcome="y_cont", exposure="x")
    assert derived_exposure(present, SPEC_TEXT, AVAILABLE, PROFILE) == present
    unknown = make_spec("ols", outcome="y_cont", exposure="dose")
    assert derived_exposure(unknown, "dose response", AVAILABLE, PROFILE) == unknown
    two = make_spec("ols", outcome="y_cont", exposure="flag")
    text = "flag = (variant == 'treatment') | (tri == 'a')"
    assert derived_exposure(two, text, AVAILABLE, PROFILE) == two
