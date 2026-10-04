from __future__ import annotations

import pytest
from pydantic import ValidationError

from borges.analysis.model_spec.schema import ModelSpecOutput


def test_unsupported_spec_needs_only_a_reason() -> None:
    spec = ModelSpecOutput.model_validate({"supported": False, "reason": "mixed model"})
    assert spec.family is None and spec.covariates == [] and spec.cov_type == "nonrobust"


def test_defaults_of_a_supported_spec() -> None:
    spec = ModelSpecOutput(supported=True, family="ols", outcome="y", exposure="x")
    assert spec.report == "coefficient" and not spec.covariates_from_ctx and spec.moderator is None


@pytest.mark.parametrize(
    "field", [("family", "gee"), ("cov_type", "HC4"), ("report", "hazard_ratio")]
)
def test_invented_values_are_rejected(field: tuple[str, str]) -> None:
    with pytest.raises(ValidationError):
        ModelSpecOutput.model_validate({"supported": True, field[0]: field[1]})


def test_exposure_level_defaults_to_none_and_marginal_effect_is_a_report() -> None:
    spec = ModelSpecOutput(
        supported=True,
        family="logit",
        outcome="y",
        exposure="x",
        exposure_level="treatment",
        report="marginal_effect",
    )
    assert spec.exposure_level == "treatment" and spec.report == "marginal_effect"
    assert ModelSpecOutput(supported=False).exposure_level is None
