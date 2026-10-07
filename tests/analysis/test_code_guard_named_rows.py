from __future__ import annotations

import pytest

from borges.analysis.code_guard_named_rows import named_rows_only_violations

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


RUN_34 = """
def apply(df, ctx):
    df = df.copy()
    if "cycle_day" not in df.columns:
        cycle_day = (28 - df["days_to_next"]).clip(1, 28)
        mask15_16 = df["WorkerID"].isin([15, 16])
        df.loc[mask15_16, "cycle_day"] = [11, 18]
        cycle_day = df["cycle_day"]
    df["high_fertility"] = ((cycle_day >= 7) & (cycle_day <= 14)).astype(int)
    return df
"""


RUN_38 = """
def apply(df, ctx):
    df = df.copy()
    cycle_day = (28 - df['days_to_next']).clip(lower=1, upper=28)
    df.loc[[15, 16], 'cycle_day'] = [11, 18]
    mask = cycle_day.between(7, 14) | cycle_day.between(17, 25)
    return df[mask].reset_index(drop=True)
"""


@pytest.mark.parametrize("code", [RUN_30, RUN_31, RUN_34, RUN_38])
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
