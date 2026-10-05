from __future__ import annotations

import ast

from borges.analysis.code_guard_fallback import (
    fallback_violations,
    share_p_value_violations,
    substituted_value_violations,
)

FALLBACK = """
def estimate(df, ctx):
    try:
        m = smf.logit('y ~ x + C(g)', data=df).fit()
    except Exception as e:
        m = smf.logit('y ~ x', data=df).fit()
    return m
"""


def test_a_broad_except_that_fits_another_model_is_refused() -> None:
    [problem] = fallback_violations(ast.parse(FALLBACK))
    assert "silently changes the analysis" in problem


def test_a_bare_except_counts_as_broad() -> None:
    assert fallback_violations(ast.parse(FALLBACK.replace("except Exception as e:", "except:")))


def test_a_narrow_except_or_one_that_does_not_refit_is_allowed() -> None:
    narrow = FALLBACK.replace("except Exception as e:", "except np.linalg.LinAlgError:")
    assert fallback_violations(ast.parse(narrow)) == []
    reraise = FALLBACK.replace("m = smf.logit('y ~ x', data=df).fit()", "raise")
    assert fallback_violations(ast.parse(reraise)) == []


INVENTED = """
def estimate(df, ctx):
    beta, var = fit(df)
    try:
        cov = np.linalg.inv(hessian)
    except np.linalg.LinAlgError:
        cov = np.eye(3) * 6.25
    if not np.isfinite(beta) or var <= 0:
        beta = 0.0
        var = 1.0
    draws = np.random.normal(beta, np.sqrt(var), 2000)
    p_value = float(np.mean(np.exp(draws) > 1))
    return {"estimate": float(np.exp(beta)), "p_value": p_value}
"""


def test_fixed_values_substituted_for_a_failed_fit_are_refused() -> None:
    problems = substituted_value_violations(ast.parse(INVENTED))
    assert len(problems) == 3 and all("invents a result" in p for p in problems)
    assert any("beta = 0.0" in p for p in problems) and any("np.eye" in p for p in problems)


def test_a_branch_that_raises_or_assigns_nan_is_not_an_invented_result() -> None:
    code = (
        "def estimate(df, ctx):\n"
        "    if not np.isfinite(beta):\n"
        "        beta = 0.0\n"
        "        raise ValueError('not finite')\n"
        "    if np.isnan(se):\n"
        "        se = np.nan\n"
        "    return beta\n"
    )
    assert substituted_value_violations(ast.parse(code)) == []


def test_a_share_of_draws_is_not_a_p_value() -> None:
    [problem] = share_p_value_violations(ast.parse(INVENTED))
    assert "not a two-sided p-value" in problem
    fine = "def estimate(df, ctx):\n    p_value = float(fit.pvalues['x'])\n    return p_value\n"
    assert share_p_value_violations(ast.parse(fine)) == []
