from __future__ import annotations

import pytest

from borges.analysis.model_spec.validate import validate_spec
from borges.analysis.model_spec.validate_weights import WEIGHTED_EXPOSURE
from borges.analysis.models import ColumnProfile, DatasetProfile
from tests.analysis.model_spec.data import make_spec

AVAILABLE = ["x", "m", "a", "g", "w", "y_cont", "y_bin", "y_count", "games", "label"]


def problems(family: str = "ols", **fields: object) -> list[str]:
    return validate_spec(make_spec(family, **fields), AVAILABLE)


def test_a_valid_weighted_and_a_valid_mixed_spec_have_no_problems() -> None:
    assert problems(weights="w", cov_type="HC3") == []
    assert problems("logit", weights="w", cov_type="cluster", cluster="g") == []
    assert problems(random_intercept="g") == []
    assert problems(random_intercept="g", moderator="m") == []


def test_weights_may_not_be_a_variable_of_the_model() -> None:
    assert WEIGHTED_EXPOSURE in problems(weights="x")
    assert any("outcome" in p for p in problems(weights="y_cont"))
    assert any("moderator" in p for p in problems(weights="m", moderator="m"))


def test_unknown_weights_and_group_columns_are_refused() -> None:
    assert any("not available" in p for p in problems(weights="nope"))
    assert any("not available" in p for p in problems(random_intercept="nope"))


def test_weights_cannot_be_text() -> None:
    column = ColumnProfile(name="label", dtype="object", n_missing=0, n_unique=3, summary={})
    profile = DatasetProfile(name="d", n_rows=10, columns=[column])
    found = validate_spec(make_spec("ols", weights="label"), AVAILABLE, profile)
    assert any("is not numeric" in p for p in found)


def test_weights_with_gee_or_marginal_effects_are_refused() -> None:
    assert any("gee" in p for p in problems(weights="w", cov_type="gee", cluster="g"))
    found = problems("logit", weights="w", report="marginal_effect")
    assert any("marginal_effect" in p for p in found)


@pytest.mark.parametrize(
    ("family", "fields", "reason"),
    [
        ("logit", {}, "ols family only"),
        ("ols", {"cov_type": "HC3"}, "nonrobust only"),
        ("ols", {"cov_type": "cluster", "cluster": "w"}, "nonrobust only"),
        ("poisson", {"offset_log": "games"}, "ols family only"),
        ("ols", {"weights": "w"}, "not available with weights"),
        ("ols", {"offset_log": "games"}, "not available with an offset"),
        ("ols", {"random_intercept": "x"}, "not a group"),
    ],
)
def test_random_intercept_combinations_name_the_reason(
    family: str, fields: dict, reason: str
) -> None:
    fields = {"random_intercept": "g", **fields}
    assert any(reason in p for p in problems(family, **fields))
