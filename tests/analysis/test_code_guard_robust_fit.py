from __future__ import annotations

import ast

from borges.analysis.code_guard_estimator import estimator_violations

OLS = "import statsmodels.api as sm\nfit = sm.OLS(y, x).fit()\n"
RLM = "import statsmodels.api as sm\nfit = sm.RLM(y, x, M=sm.robust.norms.TukeyBiweight()).fit()\n"


def test_an_mm_label_fitted_by_ols_is_flagged() -> None:
    found = estimator_violations(ast.parse(OLS), "Use MM-estimation robust regression")
    assert found and "robust or quantile regression" in found[0]


def test_a_robust_fit_or_robust_standard_errors_pass() -> None:
    assert estimator_violations(ast.parse(RLM + OLS), "Robust regression with Tukey biweight") == []
    assert estimator_violations(ast.parse(OLS), "OLS with Huber-robust standard errors") == []
    assert estimator_violations(ast.parse(OLS), "OLS with HC3 robust standard errors") == []
