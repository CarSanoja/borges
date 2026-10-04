from __future__ import annotations

import pytest

from borges.analysis.code_guard import check_code

HEADER = (
    "import numpy as np\nimport statsmodels.api as sm\nimport statsmodels.formula.api as smf\n\n"
)
ROBUST = "OLS with HC3 heteroskedasticity-robust standard errors"
CLASSICAL = "OLS with classical (non-robust) standard errors"


def model(body: str) -> str:
    return HEADER + "def estimate(df, ctx):\n" + body


def test_constructor_cov_type_is_rejected() -> None:
    code = model(
        "    X = sm.add_constant(df[['x']])\n"
        "    fit = sm.OLS(df['y'], X, cov_type='HC3').fit()\n"
        "    return {}\n"
    )
    violations = check_code(code, "model")
    assert len(violations) == 1
    assert "cov_type= passed to the OLS constructor" in violations[0]
    assert ".fit(cov_type=" in violations[0]


def test_constructor_cov_kwds_and_robust_are_rejected() -> None:
    code = model(
        "    fit = smf.logit('y ~ x', df, cov_kwds={'groups': df['g']}, robust=True).fit()\n"
        "    return {}\n"
    )
    violations = check_code(code, "model")
    assert any("cov_kwds=, robust= passed to the logit constructor" in v for v in violations)


def test_fit_with_robust_keyword_is_rejected() -> None:
    code = model("    fit = sm.OLS(df['y'], df[['x']]).fit(robust=True)\n    return {}\n")
    violations = check_code(code, "model")
    assert any("fit() has no 'robust' option" in v for v in violations)


def test_fit_cov_kwds_without_cov_type_is_rejected() -> None:
    code = model(
        "    fit = sm.OLS(df['y'], df[['x']]).fit(cov_kwds={'groups': df['g']})\n    return {}\n"
    )
    violations = check_code(code, "model")
    assert any("cov_kwds without cov_type" in v for v in violations)


def test_correct_fit_cov_type_passes() -> None:
    code = model(
        "    fit = sm.OLS(df['y'], df[['x']]).fit(cov_type='HC3')\n    return {'estimate': 0.0}\n"
    )
    assert check_code(code, "model", ROBUST) == []


def test_cluster_cov_type_with_kwds_passes() -> None:
    code = model(
        "    fit = smf.ols('y ~ x', df).fit(cov_type='cluster', cov_kwds={'groups': df['g']})\n"
        "    return {'estimate': 0.0}\n"
    )
    assert check_code(code, "model", "OLS with clustered standard errors by site") == []


def test_robust_label_without_cov_type_is_flagged() -> None:
    code = model("    fit = sm.OLS(df['y'], df[['x']]).fit()\n    return {'estimate': 0.0}\n")
    violations = check_code(code, "model", ROBUST)
    assert len(violations) == 1
    assert "never passes cov_type to fit()" in violations[0]


def test_robust_label_via_get_robustcov_results_passes() -> None:
    code = model(
        "    fit = sm.OLS(df['y'], df[['x']]).fit().get_robustcov_results(cov_type='HC3')\n"
        "    return {'estimate': 0.0}\n"
    )
    assert check_code(code, "model", ROBUST) == []


def test_classical_label_without_cov_type_passes() -> None:
    code = model("    fit = sm.OLS(df['y'], df[['x']]).fit()\n    return {'estimate': 0.0}\n")
    assert check_code(code, "model", CLASSICAL) == []
    assert check_code(code, "model", "") == []


def test_robust_to_outliers_wording_is_not_a_covariance_claim() -> None:
    code = model("    fit = sm.OLS(df['y'], df[['x']]).fit()\n    return {'estimate': 0.0}\n")
    assert check_code(code, "model", "OLS on winsorised data, robust to outliers") == []


def test_manual_numpy_model_with_robust_label_is_not_flagged() -> None:
    code = (
        "import numpy as np\n\ndef estimate(df, ctx):\n"
        "    return {'estimate': float(np.mean(df['y']))}\n"
    )
    assert check_code(code, "model", ROBUST) == []


def test_non_model_steps_are_unaffected() -> None:
    code = "def apply(df, ctx):\n    return df\n"
    assert check_code(code, "filter", ROBUST) == []


@pytest.mark.parametrize(
    "call",
    [
        "sm.Logit(df['y'], X, weights=df['w'])",
        "smf.logit('y ~ x', df, weights=df['w'])",
        "sm.GLM(df['y'], X, family=sm.families.Binomial(), weights=df['w'])",
    ],
)
def test_weights_a_model_ignores_are_rejected(call: str) -> None:
    code = model(f"    X = sm.add_constant(df[['x']])\n    fit = {call}.fit()\n    return {{}}\n")
    violations = check_code(code, "model")
    assert len(violations) == 1 and "silently ignored" in violations[0]
    assert "freq_weights" in violations[0]


def test_wls_weights_pass() -> None:
    code = model(
        "    X = sm.add_constant(df[['x']])\n"
        "    fit = sm.WLS(df['y'], X, weights=df['w']).fit()\n"
        "    return {}\n"
    )
    assert check_code(code, "model") == []
