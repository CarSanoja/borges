from __future__ import annotations

from borges.analysis.rebuild_names import rebuilt_names

RECOMPUTED = """
def apply(df, ctx):
    df = df.copy()
    gap = (df['last'] - df['before']).dt.days
    df['cycle_day'] = (28 - gap).clip(1, 28)
    df['high'] = (df['cycle_day'] <= 14).astype(int)
    return df
"""


def test_a_column_assigned_before_it_is_read_is_rebuilt() -> None:
    assert rebuilt_names(RECOMPUTED) == ["cycle_day", "high"]


def test_a_column_read_first_is_not_rebuilt() -> None:
    code = "def apply(df, ctx):\n    cd = df['x'].clip(1, 2)\n    df['x'] = cd\n    return df\n"
    assert rebuilt_names(code) == []


def test_an_assignment_that_reads_the_column_is_not_a_rebuild() -> None:
    code = "def apply(df, ctx):\n    df['x'] = df['x'].astype(float)\n    return df\n"
    assert rebuilt_names(code) == []


def test_a_partial_update_counts_as_a_read() -> None:
    code = "def apply(df, ctx):\n    df.loc[df['a'] > 1, 'x'] = 0\n    df['x'] = 1\n    return df\n"
    assert rebuilt_names(code) == []


def test_assign_keywords_are_writes() -> None:
    code = "def apply(df, ctx):\n    return df.assign(z=1, x=df['x'] * 2)\n"
    assert rebuilt_names(code) == ["z"]


def test_code_that_does_not_parse_has_no_candidates() -> None:
    assert rebuilt_names("def apply(df, ctx) return df") == []
