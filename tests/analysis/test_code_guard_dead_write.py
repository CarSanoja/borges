from __future__ import annotations

import pytest

from borges.analysis.code_guard_dead_write import dead_write_violations

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
