from __future__ import annotations

import ast

from borges.analysis.code_guard_fallback import fallback_violations

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
