from __future__ import annotations

import ast

from borges.analysis.code_guard import check_code
from borges.analysis.code_guard_literal import (
    literal_result_violations,
    widened_interval_violations,
)

ZERO_VARIANCE = """
def estimate(df, ctx):
    data = df.dropna(subset=['fertile', 'religiosity']).copy()
    if data['fertile'].var() == 0:
        n = len(data)
        return {'estimate': 0.0, 'ci_low': -0.1, 'ci_high': 0.1, 'p_value': 1.0, 'n': int(n)}
    res = smf.ols('religiosity ~ fertile', data=data).fit(cov_type='HC2')
    low, high = res.conf_int().loc['fertile']
    return {'estimate': float(res.params['fertile']), 'ci_low': float(low),
            'ci_high': float(high), 'p_value': float(res.pvalues['fertile']), 'n': len(data)}
"""

ASSIGNED = """
def estimate(df, ctx):
    X = sm.add_constant(df[['fertile', 'commitment']])
    if np.linalg.matrix_rank(X) < X.shape[1]:
        b_int = 0.0
        ci_low = 0.0
        ci_high = 0.0
        p_val = 1.0
        return {"estimate": float(b_int), "ci_low": float(ci_low), "ci_high": float(ci_high),
                "p_value": float(p_val), "n": len(df)}
    res = sm.OLS(df['religiosity'], X).fit()
    low, high = res.conf_int().loc['fertile']
    return {"estimate": float(res.params['fertile']), "ci_low": low, "ci_high": high,
            "p_value": res.pvalues['fertile'], "n": len(df)}
"""

WIDENED = """
def estimate(df, ctx):
    res = smf.ols('y ~ x', data=df).fit(cov_type='HC2')
    ci_low, ci_high = res.conf_int().loc['x']
    if ci_low == ci_high:
        ci_low = ci_low - 0.05
        ci_high += 0.05
    return {'estimate': res.params['x'], 'ci_low': ci_low, 'ci_high': ci_high,
            'p_value': res.pvalues['x'], 'n': len(df)}
"""

HONEST = """
def estimate(df, ctx):
    se = 0.0
    res = smf.ols('y ~ x', data=df).fit(cov_type='HC2')
    se = float(res.bse['x'])
    ci_low = res.params['x'] - 1.96 * se
    ci_high = res.params['x'] + 1.96 * se
    return {'estimate': float(res.params['x']), 'ci_low': ci_low, 'ci_high': ci_high,
            'p_value': float(res.pvalues['x']), 'n': len(df)}
"""


def test_a_literal_result_returned_when_the_exposure_does_not_vary_is_refused() -> None:
    problems = literal_result_violations(ast.parse(ZERO_VARIANCE))
    assert len(problems) == 4
    assert all("invents a result" in p for p in problems)
    assert any("fixed estimate (0.0)" in p for p in problems)


def test_constants_assigned_in_the_branch_that_returns_them_are_refused() -> None:
    problems = literal_result_violations(ast.parse(ASSIGNED))
    assert {p.split("fixed ")[1].split(" ")[0] for p in problems} == {
        "estimate",
        "ci_low",
        "ci_high",
        "p_value",
    }


def test_an_interval_bound_moved_by_a_constant_is_refused() -> None:
    problems = widened_interval_violations(ast.parse(WIDENED))
    assert len(problems) == 2 and all("fixed amount" in p for p in problems)


def test_results_computed_from_the_fit_are_allowed() -> None:
    tree = ast.parse(HONEST)
    assert literal_result_violations(tree) == []
    assert widened_interval_violations(tree) == []


def test_the_model_guard_refuses_the_recorded_repair() -> None:
    assert any("invents a result" in p for p in check_code(ZERO_VARIANCE, "model"))
