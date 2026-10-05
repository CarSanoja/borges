from __future__ import annotations

import pytest

from borges.analysis.model_spec.unfit_family import WEIGHTED_SKIP, unfit_reason


@pytest.mark.parametrize(
    "intent",
    [
        "GLM with Gamma family and log link",
        "Logistic regression with complementary log-log link",
        "Negative binomial regression with referee random effects",
        "Ordered logit of the rating",
        "Median quantile regression",
    ],
)
def test_models_the_templates_do_not_fit_are_named(intent: str) -> None:
    reason = unfit_reason(intent)
    assert reason is not None and reason.startswith("the option names a model the templates")


def test_weights_and_template_models_are_told_apart() -> None:
    assert unfit_reason("Weighted least squares by inverse variance") == WEIGHTED_SKIP
    assert unfit_reason("Poisson regression with robust SE, adjusting for weight") is None
    assert unfit_reason("Logistic regression with cluster-robust SEs") is None
