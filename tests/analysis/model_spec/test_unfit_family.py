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


@pytest.mark.parametrize(
    "intent",
    [
        "WLS (weights = students) with cluster-robust SEs (prof)",
        "Linear mixed model (random intercept for prof)",
        "Weighted logistic regression by sampling weight",
        "MixedLM with a random intercept per school",
    ],
)
def test_options_the_spec_can_carry_are_not_skipped(intent: str) -> None:
    assert unfit_reason(intent) is None


@pytest.mark.parametrize(
    "intent",
    [
        "Mixed model with random slopes for prof",
        "Random intercept and random slope for prof",
        "Mixed model with crossed random effects for prof and course",
        "Generalized linear mixed model (GLMM) with a random intercept",
        "Probit regression",
        "WLS with inverse probability weights",
        "Weighted mixed model with a random intercept for prof",
    ],
)
def test_options_the_templates_still_cannot_fit_stay_skipped(intent: str) -> None:
    assert unfit_reason(intent) is not None
