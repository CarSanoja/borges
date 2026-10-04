from __future__ import annotations

import ast

import pytest

from borges.analysis.code_guard_estimator import estimator_violations, named_family
from borges.analysis.model_spec.render import render_code
from tests.analysis.model_spec.data import make_spec


def violations(family: str, intent: str) -> list[str]:
    tree = ast.parse(render_code(make_spec(family, report="rate_ratio")))
    return estimator_violations(tree, intent)


@pytest.mark.parametrize(
    ("intent", "family"),
    [
        ("Quasi-Poisson regression", "quasipoisson"),
        ("quasipoisson GLM with HC2", "quasipoisson"),
        ("Negative binomial regression with robust SE", "negbin"),
        ("Poisson regression with robust SE", "poisson"),
        ("Logistic regression, clustered by month", "logit"),
        ("OLS with HC3", None),
        ("Negative binomial instead of Poisson", None),
    ],
)
def test_the_named_family_is_read_from_the_option(intent: str, family: str | None) -> None:
    assert named_family(intent) == family


def test_a_quasi_poisson_label_on_a_negative_binomial_fit_is_refused() -> None:
    [problem] = violations("negbin", "Quasi-Poisson regression with elapsed years")
    assert "quasi-Poisson" in problem and 'scale="X2"' in problem


def test_the_quasi_poisson_template_matches_its_label() -> None:
    assert violations("quasipoisson", "Quasi-Poisson regression") == []


def test_a_plain_poisson_fit_is_not_quasi_poisson() -> None:
    assert violations("poisson", "Quasi-Poisson regression")


def test_a_poisson_label_on_a_negative_binomial_fit_is_refused() -> None:
    [problem] = violations("negbin", "Poisson regression with robust SE")
    assert "negative binomial" in problem


def test_matching_labels_pass() -> None:
    assert violations("negbin", "Negative binomial regression") == []
    assert violations("poisson", "Poisson regression with HC0") == []


def test_code_without_a_model_is_not_judged() -> None:
    tree = ast.parse("def estimate(df, ctx):\n    return {}\n")
    assert estimator_violations(tree, "Poisson regression") == []
