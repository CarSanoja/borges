from __future__ import annotations

import pytest

from borges.analysis.code_guard_ctx_value import ctx_value_violations
from tests.analysis.test_code_guard_ctx import plan, step

ONSET = step("s2", "Next onset", "transform", "Write ctx['next_onset'] = 'next_onset'.")
DAY = step("s3", "Cycle day", "transform", "cycle day = 28 minus days to next onset")
WRITES = (
    "def apply(df, ctx):\n"
    "    df['next_onset'] = df['x']\n"
    "    ctx['next_onset'] = 'next_onset'\n"
    "    return df\n"
)


def checked(body: str) -> list[str]:
    onset = ONSET.model_copy(deep=True)
    onset.options[0].code = WRITES
    return ctx_value_violations(
        f"def apply(df, ctx):\n{body}\n    return df\n", plan(onset, DAY), DAY
    )


@pytest.mark.parametrize(
    "body",
    [
        "    df['d'] = (df['DateTesting'] - ctx['next_onset']).dt.days",
        "    df['d'] = ctx.get('next_onset') - df['DateTesting']",
        "    keep = ctx['next_onset'] >= 7",
        "    keep = ctx['next_onset'] == 'high'",
    ],
)
def test_a_column_name_used_as_data_is_refused(body: str) -> None:
    """fertility_vote on 7 October, runs 18 and 21: a date minus the string 'next_onset', and
    the string 'cycle_day' compared with 7."""
    found = checked(body)
    assert found and "holds the column name 'next_onset'" in found[0]
    assert "df[ctx['next_onset']]" in found[0]


@pytest.mark.parametrize(
    "body",
    [
        "    df['d'] = (df[ctx['next_onset']] - df['DateTesting']).dt.days",
        "    df[ctx['next_onset'] + '_copy'] = 1",
        "    df[f\"{ctx['next_onset']}_x\"] = 1",
        "    same = ctx['next_onset'] == 'next_onset'",
        "    name = ctx['next_onset']\n    df['d'] = df[name] - df['DateTesting']",
        "    present = ctx['next_onset'] in df.columns",
        "    formula = 'y ~ ' + ctx['next_onset']",
        "    other = ctx.get('next_onset') != 'outcome'",
    ],
)
def test_reading_the_column_through_its_name_passes(body: str) -> None:
    assert checked(body) == []


def test_a_key_no_earlier_step_sets_to_a_column_name_is_left_alone() -> None:
    days = step("s1", "Days", "transform", "Set ctx['window'] = 7.")
    code = "def apply(df, ctx):\n    keep = df['d'] >= ctx['window'] - 1\n    return df[keep]\n"
    assert ctx_value_violations(code, plan(days, DAY), DAY) == []
