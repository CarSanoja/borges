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
    "field", [("family", "gee"), ("cov_type", "HC0"), ("report", "hazard_ratio")]
)
def test_invented_values_are_rejected(field: tuple[str, str]) -> None:
    with pytest.raises(ValidationError):
        ModelSpecOutput.model_validate({"supported": True, field[0]: field[1]})
