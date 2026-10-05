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


def test_a_link_class_instead_of_an_instance_is_refused() -> None:
    body = (
        "import statsmodels.api as sm\n\n\n"
        "def estimate(df, ctx):\n"
        "    fam = sm.families.Binomial(link=sm.families.links.Logit{call})\n"
        "    fit = sm.GLM(df['y'], df[['x']], family=fam).fit()\n"
        "    return float(fit.params['x'])\n"
    )
    found = check_code(body.format(call=""), "model")
    assert any("link= takes an instance" in v for v in found)
    assert not any("link=" in v for v in check_code(body.format(call="()"), "model"))


def test_the_link_hint_names_the_class_the_code_used() -> None:
    body = (
        "import statsmodels.api as sm\n\n\n"
        "def estimate(df, ctx):\n"
        "    fam = sm.families.Binomial(link=sm.families.links.CLogLog)\n"
        "    fit = sm.GLM(df['y'], df[['x']], family=fam).fit()\n"
        "    return float(fit.params['x'])\n"
    )
    found = check_code(body, "model")
    assert any("write link=sm.families.links.CLogLog()" in v for v in found)


@pytest.mark.parametrize(
    ("intent", "robust"),
    [
        ("Logistic regression with cluster-robust SEs", True),
        (
            "Logistic regression with model-based SEs Same as opt_logit but use default "
            "(model-based) covariance instead of cluster-robust. (opt_logit: Use HC0 "
            "cluster-robust covariance.)",
            False,
        ),
        ("Logit with HC3 robust standard errors rather than model-based ones", True),
        ("OLS clustered by country: same regression but cluster standard errors", True),
    ],
)
def test_robust_errors_are_read_from_the_option_own_words(intent: str, robust: bool) -> None:
    from borges.analysis.code_guard_statsmodels import robust_intended

    assert robust_intended(intent) is robust


@pytest.mark.parametrize(
    ("label", "cov", "refused"),
    [
        ("OLS with i.i.d. standard errors", 'cov_type="HC1"', True),
        ("OLS with i.i.d. standard errors", 'cov_type="nonrobust"', False),
        ("OLS with HC3 robust standard errors", 'cov_type="HC1"', True),
        ("OLS with HC3 robust standard errors", 'cov_type="HC3"', False),
        ("OLS clustered by country", 'cov_type="cluster", cov_kwds={"groups": g}', False),
    ],
)
def test_the_standard_errors_a_label_names_are_the_ones_fitted(
    label: str, cov: str, refused: bool
) -> None:
    from borges.analysis.code_guard_se_label import se_label_violations

    code = (
        "def estimate(df, ctx):\n    g = df['c']\n"
        f"    fit = sm.OLS(df['y'], df[['x']]).fit({cov})\n    return fit\n"
    )
    import ast

    assert bool(se_label_violations(ast.parse(code), label)) is refused
