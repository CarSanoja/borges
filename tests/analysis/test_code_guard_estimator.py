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


def test_a_penalised_option_fitted_by_plain_likelihood_is_refused() -> None:
    [problem] = violations("logit", "Firth logistic regression to reduce small-sample bias")
    assert "penalised fit" in problem
    assert violations("logit", "Logistic regression, unpenalized, HC1") == []
    lasso = ast.parse(
        "import statsmodels.api as sm\n"
        "def estimate(df, ctx):\n"
        "    fit = sm.Logit(df['y'], df[['x']]).fit_regularized(method='l1', alpha=1.0)\n"
    )
    assert estimator_violations(lasso, "Lasso logistic regression") == []


WLS_CODE = (
    "import statsmodels.api as sm\n\n\ndef estimate(df, ctx):\n"
    "    fit = sm.WLS(df['y'], sm.add_constant(df[['x']]), weights=df['w']).fit()\n"
    "    return fit\n"
)
GLM_WEIGHTED = (
    "import statsmodels.api as sm\n\n\ndef estimate(df, ctx):\n"
    "    fit = sm.GLM(df['y'], df[['x']], var_weights=df['w']).fit()\n    return fit\n"
)


def test_a_weighted_label_on_an_unweighted_fit_is_refused() -> None:
    [problem] = violations("ols", "Weighted OLS by session length")
    assert "weighted fit" in problem and "WLS" in problem


@pytest.mark.parametrize("code", [WLS_CODE, GLM_WEIGHTED])
def test_a_weighted_fit_passes(code: str) -> None:
    assert estimator_violations(ast.parse(code), "Weighted least squares by inverse variance") == []


def test_robust_weights_and_unweighted_labels_are_not_weighted_fits() -> None:
    assert violations("ols", "OLS with HC3 standard errors, unweighted") == []
    robust = estimator_violations(ast.parse(WLS_CODE), "Huber weights robust regression")
    assert all("weighted fit" not in problem for problem in robust)


def test_a_covariate_called_weight_is_no_weighted_fit() -> None:
    assert violations("ols", "OLS adjusting for height and weight") == []


def test_a_quasi_poisson_label_on_a_robust_poisson_fit_is_refused() -> None:
    tree = ast.parse(render_code(make_spec("poisson", report="rate_ratio", cov_type="HC0")))
    source = ast.unparse(tree).replace("model.fit(", 'model.fit(scale="X2", ')
    [problem] = estimator_violations(ast.parse(source), "Quasi-Poisson regression")
    assert "statsmodels ignores the scale" in problem
