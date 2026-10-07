from __future__ import annotations

import pytest

from borges.analysis.code_guard_ctx_unset import unset_ctx_violations
from tests.analysis.test_code_guard_ctx import plan, step

LENGTH = step("s1", "Cycle length", "transform", "Write ctx['cycle_length_col'] = 'cycle_length'.")
ONSET = step("s2", "Next onset", "transform", "next onset = last period + cycle length")
DEAD = """
def apply(df, ctx):
    col = ctx['cycle_length_col']
    if ctx.get('next_onset_option') == 'next_onset_add':
        df['next_onset'] = df['StartDateofLastPeriod'] + pd.to_timedelta(df[col], unit='D')
    else:
        df['next_onset'] = df['StartDateofLastPeriod']
    return df
"""


def test_a_branch_on_a_key_no_step_sets_is_refused() -> None:
    """fertility_vote on 7 October, run 22: the spec's formula sat in a dead branch."""
    found = unset_ctx_violations(DEAD, plan(LENGTH, ONSET), ONSET)
    assert len(found) == 1 and "ctx['next_onset_option']" in found[0]


@pytest.mark.parametrize(
    "body",
    [
        "    col = ctx['cycle_length_col']",
        "    ctx['own'] = 'x'\n    col = ctx['own']",
        "    covs = ctx.get('covariates', [])",
        "    extra = list(ctx.get('columns', []))",
    ],
)
def test_keys_set_earlier_by_the_code_itself_or_by_the_harness_pass(body: str) -> None:
    code = f"def apply(df, ctx):\n{body}\n    return df\n"
    assert unset_ctx_violations(code, plan(LENGTH, ONSET), ONSET) == []
