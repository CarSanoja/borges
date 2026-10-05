from __future__ import annotations

import pytest

from borges.analysis.code_guard_ctx_spec import (
    positional_dummy_violations,
    sibling_outcome_violations,
    spec_ctx_write_violations,
)
from borges.analysis.models import Option, Step

PLATFORM = """import pandas as pd

def apply(df, ctx):
    dummies = pd.get_dummies(df["platform"], drop_first=True, dtype=float)
    dummies.columns = ["platform_ios", "platform_android"]
    return pd.concat([df, dummies], axis=1)
"""
PLATFORM_SPEC = (
    "Convert platform to dummy variables with drop_first=True. "
    "Set ctx['covariates'] to ['platform_ios', 'platform_android']."
)


def test_the_checkout_option_that_never_set_its_covariates_is_flagged() -> None:
    [problem] = spec_ctx_write_violations(PLATFORM, PLATFORM_SPEC)
    assert "never writes ctx['covariates']" in problem


def test_positional_renaming_of_dummies_is_flagged() -> None:
    [problem] = positional_dummy_violations(PLATFORM)
    assert "renamed by position" in problem


@pytest.mark.parametrize(
    "body",
    [
        "    ctx['outcome'] = 'wb_psych_mean'\n    ctx['covariates'] = ['x']\n    return df",
        "    ctx.update({'outcome': 'wb_psych_mean', 'covariates': ['x']})\n    return df",
        "    ctx['covariates'].append('x')\n    ctx['outcome'] = 'y'\n    return df",
    ],
)
def test_code_that_writes_the_promised_keys_passes(body: str) -> None:
    spec = "Write ctx['outcome'] = wb_psych_mean and set ctx['covariates'] to ['x']."
    code = f"def apply(df, ctx):\n{body}\n"
    assert spec_ctx_write_violations(code, spec) == []


def test_a_marp_outcome_option_that_only_builds_a_column_is_flagged() -> None:
    code = "def apply(df, ctx):\n    return df.assign(outcome=df['wb_psych_mean'])\n"
    spec = "Use wb_psych_mean as the outcome. Write ctx['outcome'] = wb_psych_mean."
    assert spec_ctx_write_violations(code, spec)


def test_a_column_named_in_ctx_notation_is_not_held_to_the_spec() -> None:
    code = "def apply(df, ctx):\n    df['skin_tone'] = (df['r1'] + df['r2']) / 2\n    return df\n"
    spec = "Compute ctx['skin_tone'] = (rater1 + rater2) / 2."
    assert spec_ctx_write_violations(code, spec) == []


def test_dummies_picked_by_name_pass() -> None:
    code = (
        "import pandas as pd\n\ndef apply(df, ctx):\n"
        "    dummies = pd.get_dummies(df['platform'], prefix='platform', dtype=float)\n"
        "    ctx['covariates'] = ['platform_ios', 'platform_web']\n"
        "    return df.join(dummies[['platform_ios', 'platform_web']])\n"
    )
    assert positional_dummy_violations(code) == []


def test_a_promise_to_write_to_ctx_is_held_to_the_spec() -> None:
    code = "def apply(df, ctx):\n    df['outcome'] = df['wb_overall_mean']\n    return df\n"
    spec = (
        "Use wb_overall_mean as the outcome; write to ctx['outcome'] the value of wb_overall_mean."
    )
    [problem] = spec_ctx_write_violations(code, spec)
    assert "never writes ctx['outcome']" in problem


def test_an_option_whose_siblings_write_the_outcome_must_write_it_too() -> None:
    silent = "def apply(df, ctx):\n    return df.assign(outcome=df['wb_overall_mean'])\n"
    psych = "def apply(df, ctx):\n    ctx['outcome'] = 'wb_psych_mean'\n    return df\n"
    overall = Option(id="o", label="Overall", rationale="r", spec="Use overall.", is_default=True)
    other = Option(id="p", label="Psych", rationale="r", spec="Use psych.", code=psych)
    step = Step(id="s", title="Outcome", kind="feature", description="d", options=[overall, other])
    [problem] = sibling_outcome_violations(silent, step, overall)
    assert "other options of this step write ctx['outcome']" in problem
    assert sibling_outcome_violations(psych.replace("psych", "overall"), step, overall) == []
    lone = step.model_copy(update={"options": [overall]})
    assert sibling_outcome_violations(silent, lone, overall) == []
