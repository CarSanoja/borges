from __future__ import annotations

from borges.analysis.model_spec.validate import validate_spec
from borges.analysis.models import ColumnProfile, Comparator, DatasetProfile, DecisionRule
from tests.analysis.model_spec.data import make_spec

AVAILABLE = ["variant", "x", "wide", "tri", "y_bin", "y_cont", "m"]
PP_RULE = DecisionRule(
    metric="conversion lift, treatment minus control (percentage points)",
    comparator=Comparator.GT,
    threshold=0.0,
)
RATIO_RULE = DecisionRule(metric="risk ratio", comparator=Comparator.GT, threshold=1.0)


def column(name: str, dtype: str, unique: int, **summary: object) -> ColumnProfile:
    return ColumnProfile(name=name, dtype=dtype, n_missing=0, n_unique=unique, summary=summary)


PROFILE = DatasetProfile(
    name="t",
    n_rows=100,
    columns=[
        column("variant", "str", 2, top_1="treatment: 15171", top_2="control: 14755"),
        column("tri", "object", 3, top_1="a: 5", top_2="b: 4", top_3="c: 3"),
        column("x", "float64", 2, min=0.0, max=1.0),
        column("wide", "float64", 30, min=0.0, max=1.0),
        column("y_bin", "float64", 2, min=0.0, max=1.0),
        column("y_cont", "float64", 90, min=-3.0, max=3.0),
        column("m", "float64", 40, min=0.0, max=1.0),
    ],
)


def problems(family: str, rule: DecisionRule | None = None, **fields: object) -> list[str]:
    outcome = "y_bin" if family == "logit" else "y_cont"
    spec = make_spec(family, outcome=outcome, **fields)
    return validate_spec(spec, AVAILABLE, PROFILE, rule)


def test_a_two_level_text_exposure_with_a_named_level_is_accepted() -> None:
    assert problems("ols", exposure="variant", exposure_level="treatment") == []
    assert problems("ols", exposure="variant", exposure_level="control") == []


def test_a_text_exposure_needs_a_level_that_exists() -> None:
    assert any("exposure_level" in p for p in problems("ols", exposure="variant"))
    missing = problems("ols", exposure="variant", exposure_level="variant_treat")
    assert any("not a listed level" in p for p in missing)


def test_a_listed_level_of_a_multi_level_text_exposure_is_one_against_the_rest() -> None:
    assert problems("ols", exposure="tri", exposure_level="b") == []
    unknown = problems("ols", exposure="tri", exposure_level="d")
    assert any("not a listed level" in p for p in unknown)


def test_a_text_exposure_with_too_many_levels_is_refused() -> None:
    many = DatasetProfile(
        name="t", n_rows=100, columns=[*PROFILE.columns[1:], column("variant", "str", 40)]
    )
    spec = make_spec("ols", outcome="y_cont", exposure="variant", exposure_level="treatment")
    assert any("40 levels" in p for p in validate_spec(spec, AVAILABLE, many, None))


def test_a_numeric_exposure_must_not_set_a_level() -> None:
    assert any("numeric" in p for p in problems("ols", exposure="x", exposure_level="1"))
    assert problems("ols", exposure="x") == []


def test_a_text_exposure_is_still_refused_as_a_moderator_without_a_level() -> None:
    assert any("not numeric" in p for p in problems("ols", exposure="variant", moderator="tri"))


def test_marginal_effect_is_the_logit_report_for_a_difference_in_proportions() -> None:
    fields = {"exposure": "variant", "exposure_level": "treatment"}
    assert problems("logit", PP_RULE, report="marginal_effect", **fields) == []
    refused = problems("logit", PP_RULE, **fields)
    assert any("difference in proportions" in p for p in refused)
    assert problems("ols", PP_RULE, **fields) == []


def test_marginal_effect_is_refused_elsewhere() -> None:
    fields = {"exposure": "x", "report": "marginal_effect"}
    assert any("not available" in p for p in problems("ols", **fields))
    assert any("moderator" in p for p in problems("logit", moderator="m", **fields))
    assert any("ratio" in p for p in problems("logit", RATIO_RULE, **fields))
    assert any("0/1" in p for p in problems("logit", exposure="wide", report="marginal_effect"))


def test_marginal_effect_refuses_a_standardized_exposure() -> None:
    result = problems("logit", PP_RULE, exposure="x", report="marginal_effect", standardize=["x"])
    assert any("unscaled" in p for p in result)


def test_marginal_effect_needs_a_zero_one_numeric_exposure() -> None:
    PROFILE.columns.append(column("coded12", "float64", 2, min=1.0, max=2.0))
    try:
        result = problems("logit", PP_RULE, exposure="coded12", report="marginal_effect")
    finally:
        PROFILE.columns.pop()
    assert any("0/1" in p for p in result)
    assert problems("logit", PP_RULE, exposure="x", report="marginal_effect") == []


def test_a_proportion_rule_without_percentage_points_still_needs_marginal_effect() -> None:
    rule = DecisionRule(
        metric="difference in conversion proportions, treatment minus control",
        comparator=Comparator.GT,
        threshold=0.0,
    )
    assert any("marginal_effect" in p for p in problems("logit", rule, exposure="x"))
    assert problems("logit", rule, exposure="x", report="marginal_effect") == []
    assert problems("ols", rule, exposure="x") == []
