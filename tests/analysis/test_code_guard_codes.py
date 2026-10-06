from __future__ import annotations

import ast

from borges.analysis.code_guard import check_code
from borges.analysis.code_guard_codes import category_code_violations

REPAIRED = """
def estimate(df, ctx):
    data = df.dropna(subset=['religiosity', 'fertility_high', 'rel_status'])
    core = data[['fertility_high', 'rel_status']].copy()
    core['exposure_by_moderator'] = core['fertility_high'].astype(float) * pd.Categorical(
        core['rel_status']).codes
    fit = sm.OLS(data['religiosity'], sm.add_constant(core[['fertility_high',
        'exposure_by_moderator']])).fit(cov_type='HC3')
    low, high = fit.conf_int().loc['exposure_by_moderator']
    return {'estimate': fit.params['exposure_by_moderator'], 'ci_low': low, 'ci_high': high,
            'p_value': fit.pvalues['exposure_by_moderator'], 'n': len(data)}
"""

IN_FORMULA = """
def estimate(df, ctx):
    df['status_code'] = df['rel_status'].cat.codes
    fit = smf.ols('religiosity ~ fertile * status_code', data=df).fit()
    return fit
"""

CLUSTER_GROUPS = """
def estimate(df, ctx):
    groups = pd.factorize(df['player'])[0]
    fit = smf.logit('y ~ x', data=df).fit(cov_type='cluster', cov_kwds={'groups': groups})
    return fit
"""


def test_codes_multiplied_into_an_interaction_are_refused() -> None:
    [problem] = category_code_violations(ast.parse(REPAIRED))
    assert "reverse the sign" in problem


def test_a_coded_column_named_in_a_formula_is_refused() -> None:
    assert category_code_violations(ast.parse(IN_FORMULA))


def test_codes_used_as_cluster_groups_are_allowed() -> None:
    assert category_code_violations(ast.parse(CLUSTER_GROUPS)) == []


def test_the_model_guard_refuses_the_recorded_repair() -> None:
    assert any("category codes" in p for p in check_code(REPAIRED, "model"))
