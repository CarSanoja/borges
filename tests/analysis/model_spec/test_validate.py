from __future__ import annotations

import pytest

from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.model_spec.validate import validate_spec
from borges.analysis.models import (
    ColumnProfile,
    Comparator,
    DatasetProfile,
    DecisionRule,
)
from tests.analysis.model_spec.data import make_spec

AVAILABLE = [
    "x",
    "m",
    "a",
    "cat",
    "g",
    "games",
    "y_cont",
    "y_bin",
    "y_count",
    "flag",
    "player",
    "country",
]


def column(name: str, dtype: str, unique: int, **summary: float) -> ColumnProfile:
    return ColumnProfile(name=name, dtype=dtype, n_missing=0, n_unique=unique, summary=summary)


PROFILE = DatasetProfile(
    name="t",
    n_rows=100,
    columns=[
        column("x", "float64", 2, min=0.0, max=1.0),
        column("y_cont", "float64", 90, min=-3.0, max=3.0),
        column("y_bin", "float64", 2, min=0.0, max=1.0),
        column("y_two", "float64", 2, min=1.0, max=2.0),
        column("y_text", "object", 2),
        column("y_count", "int64", 12, min=0.0, max=11.0),
        column("y_neg", "float64", 20, min=-1.0, max=11.0),
        column("y_many", "float64", 50, min=0.0, max=1.0),
        column("cat", "object", 3),
        column("player", "object", 1577),
        column("country", "object", 50),
        column("games", "int64", 20, min=1.0, max=30.0),
    ],
)


def problems(spec: ModelSpecOutput, rule: DecisionRule | None = None) -> list[str]:
    return validate_spec(spec, AVAILABLE + ["y_two", "y_text", "y_neg", "y_many"], PROFILE, rule)


def test_valid_specs_have_no_problems() -> None:
    assert problems(make_spec("ols", covariates=["a", "cat"], moderator="m")) == []
    assert problems(make_spec("logit", report="odds_ratio")) == []
    assert problems(make_spec("negbin", offset_log="games", report="rate_ratio")) == []
    assert problems(make_spec("ols", cov_type="cluster", cluster="g", standardize=["x"])) == []


def test_unsupported_spec_is_a_problem() -> None:
    spec = ModelSpecOutput(supported=False, reason="mixed model")
    assert "mixed model" in problems(spec)[0]


def test_missing_required_fields() -> None:
    spec = ModelSpecOutput(supported=True)
    assert len(problems(spec)) == 3


@pytest.mark.parametrize(
    ("fields", "text"),
    [
        ({"covariates": ["ghost"]}, "ghost"),
        ({"cluster": "ghost", "cov_type": "cluster"}, "ghost"),
        ({"moderator": "ghost"}, "ghost"),
        ({"exposure": "y_cont"}, "different columns"),
        ({"moderator": "x"}, "moderator must differ"),
        ({"covariates": ["const"]}, "reserved"),
        ({"standardize": ["g"]}, "not the outcome"),
        ({"cov_type": "cluster"}, "needs a cluster"),
        ({"cluster": "g"}, "cov_type is not cluster"),
        ({"offset_log": "games"}, "only available for poisson"),
        ({"report": "odds_ratio"}, "not available for family ols"),
        ({"report": "rate_ratio"}, "not available for family ols"),
        ({"moderator": "cat"}, "not numeric"),
        ({"standardize": ["cat"], "covariates": ["cat"]}, "not numeric"),
    ],
)
def test_bad_ols_specs_are_rejected(fields: dict, text: str) -> None:
    assert any(text in p for p in problems(make_spec("ols", **fields)))


def test_family_report_pairs() -> None:
    assert any("not available" in p for p in problems(make_spec("logit", report="rate_ratio")))
    assert any("not available" in p for p in problems(make_spec("poisson", report="odds_ratio")))
    assert any("not available" in p for p in problems(make_spec("negbin", report="odds_ratio")))


def test_logit_outcome_must_be_binary() -> None:
    assert any("binary" in p for p in problems(make_spec("logit", outcome="y_cont")))
    assert any("binary" in p for p in problems(make_spec("logit", outcome="y_two")))
    assert any("binary" in p for p in problems(make_spec("logit", outcome="y_many")))
    assert any("not numeric" in p for p in problems(make_spec("logit", outcome="y_text")))
    assert problems(make_spec("logit", outcome="flag")) == []


def test_count_outcome_cannot_be_negative_or_standardized() -> None:
    assert any("negative" in p for p in problems(make_spec("poisson", outcome="y_neg")))
    assert any("standardized" in p for p in problems(make_spec("negbin", standardize=["y_count"])))


def test_decision_rule_scale() -> None:
    ratio = DecisionRule(metric="risk ratio", comparator=Comparator.GT, threshold=1.0)
    assert any("ratio" in p for p in problems(make_spec("logit"), ratio))
    assert any("ratio" in p for p in problems(make_spec("ols"), ratio))
    assert problems(make_spec("logit", report="odds_ratio"), ratio) == []
    points = DecisionRule(metric="difference in percentage points")
    assert any("proportions" in p for p in problems(make_spec("logit"), points))
    assert problems(make_spec("ols"), points) == []


def test_without_a_profile_only_structure_is_checked() -> None:
    spec = make_spec("logit", outcome="y_cont")
    assert validate_spec(spec, AVAILABLE) == []


def test_identifier_with_hundreds_of_levels_is_not_a_fixed_effect() -> None:
    found = problems(make_spec("ols", covariates=["a", "player"]))
    assert found == [
        "player has 1577 levels: use it as the cluster column, not as dummy fixed effects"
    ]


def test_the_level_limit_is_fifty_and_numeric_columns_are_exempt() -> None:
    assert problems(make_spec("ols", covariates=["country", "games"])) == []
    assert problems(make_spec("ols", cov_type="cluster", cluster="player")) == []


def test_ctx_covariates_count_only_when_the_spec_reads_the_ctx_list() -> None:
    literal = make_spec("ols", covariates=["a"])
    from_ctx = make_spec("ols", covariates=["a"], covariates_from_ctx=True)
    args = (AVAILABLE, PROFILE, None)
    assert validate_spec(literal, *args, ["player"]) == []
    found = validate_spec(from_ctx, *args, ["player"])
    assert len(found) == 1 and found[0].startswith("player has 1577 levels")
