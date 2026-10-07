from __future__ import annotations

import pytest

from borges.analysis.code_guard_dead_write import dead_write_violations, named_rows_only_violations

RUN_28 = """
def apply(df, ctx):
    df = df.copy()
    cycle_day = (28 - df['days_to_next']).clip(lower=1, upper=28)
    df.loc[df['WorkerID'] == 15, 'cycle_day'] = 11
    df.loc[df['WorkerID'] == 16, 'cycle_day'] = 18
    df['cycle_day'] = cycle_day
    return df
"""


def test_rows_set_by_hand_then_wiped_by_the_whole_column_are_reported() -> None:
    """fertility_vote on 7 October, run 28: two women lost their hand-set cycle days."""
    found = dead_write_violations(RUN_28)
    assert len(found) == 1
    assert "line 6 sets column 'cycle_day'" in found[0] and "line 7 assigns" in found[0]


@pytest.mark.parametrize(
    "code",
    [
        "def apply(df, ctx):\n    df['c'] = 1\n    df.loc[df.x > 0, 'c'] = 2\n    return df\n",
        "def apply(df, ctx):\n    df.loc[df.x > 0, 'c'] = 2\n    df['c'] = df['c'].fillna(0)\n",
        "def apply(df, ctx):\n    df.loc[df.x > 0, 'c'] = 2\n    n = df['c'].sum()\n"
        "    df['c'] = n\n",
        "def apply(df, ctx):\n    df.loc[df.x > 0, 'c'] = 2\n    df = df.copy()\n    df['c'] = 1\n",
        "def apply(df, ctx):\n    df.loc[df.x > 0, 'c'] = 2\n    df['d'] = 1\n    return df\n",
        "def apply(df, ctx):\n    df.loc[df.x > 0, 'c'] = 2\n    other['c'] = 1\n",
    ],
)
def test_a_write_that_is_read_or_kept_is_not_reported(code: str) -> None:
    assert dead_write_violations(code) == []


def test_a_whole_column_loc_write_counts_as_whole() -> None:
    code = "def apply(df, ctx):\n    df.at[3, 'c'] = 2\n    df.loc[:, 'c'] = 0\n"
    assert len(dead_write_violations(code)) == 1


RUN_31 = """
def apply(df, ctx):
    df = df.copy()
    cycle_day = (28 - df['days_to_next']).clip(lower=1, upper=28)
    df.loc[df['WorkerID'].isin([15, 16]), 'cycle_day'] = [11, 18]
    mask = ((cycle_day >= 7) & (cycle_day <= 14)) | ((cycle_day >= 17) & (cycle_day <= 25))
    return df[mask].copy()
"""
RUN_30 = """
def apply(df, ctx):
    df = df.copy()
    cycle_day = (28 - df['days_to_next']).clip(lower=1, upper=28)
    df.loc[(df['WorkerID'] == 15), 'cycle_day'] = 11
    df.loc[(df['WorkerID'] == 16), 'cycle_day'] = 18
    cycle_day = df['cycle_day']
    return df[(cycle_day >= 7) & (cycle_day <= 25)].copy()
"""


def first_step_plan():
    from tests.analysis.fakes import make_plan

    plan = make_plan(with_code=True)
    return plan, plan.steps[0]


@pytest.mark.parametrize("code", [RUN_30, RUN_31])
def test_a_column_created_only_for_rows_named_one_by_one_is_reported(code: str) -> None:
    """fertility_vote on 7 October, runs 30 and 31: the computed days stayed in a local variable
    and only the two hand-set women had a cycle day."""
    plan, step = first_step_plan()
    found = named_rows_only_violations(code, plan, step)
    assert len(found) == 1 and "column 'cycle_day' is created only" in found[0]


@pytest.mark.parametrize(
    "code",
    [
        "def apply(df, ctx):\n    m = df.x > 0\n    df.loc[m, 'c'] = 1\n    df.loc[~m, 'c'] = 0\n",
        "def apply(df, ctx):\n    df.loc[df.id == 3, 'c'] = 1\n    df['c'] = df['c'].fillna(0)\n",
        "def apply(df, ctx):\n    df.loc[df.id == 3, 'c'] = 1\n"
        "    df.fillna({'c': 0}, inplace=True)\n",
        "def apply(df, ctx):\n    df['c'] = 0\n    df.loc[df.id == 3, 'c'] = 1\n",
        "def apply(df, ctx):\n    df.loc[df.id == 3, 'outcome'] = 1\n",
    ],
)
def test_a_complete_or_known_column_is_not_reported(code: str) -> None:
    plan, step = first_step_plan()
    assert named_rows_only_violations(code, plan, step) == []
