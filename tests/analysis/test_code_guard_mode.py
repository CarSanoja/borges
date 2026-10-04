from __future__ import annotations

import ast

from borges.analysis.code_guard_mode import empty_mode_violations

UNGUARDED = """
def apply(df, ctx):
    for col in ["job", "poutcome"]:
        mode_val = df[col].mode().iloc[0]
        df[col] = df[col].fillna(mode_val)
    return df
"""
GUARDED = """
def apply(df, ctx):
    for col in ["job", "poutcome"]:
        mode = df[col].mode()
        if not mode.empty:
            df[col] = df[col].fillna(mode.iloc[0])
    return df
"""
BRACKET = "def apply(df, ctx):\n    v = df['job'].mode()[0]\n    return df.fillna({'job': v})\n"


def test_an_unguarded_first_mode_is_refused() -> None:
    [problem] = empty_mode_violations(ast.parse(UNGUARDED))
    assert problem.startswith("line 4: Series.mode() is empty")
    assert len(empty_mode_violations(ast.parse(BRACKET))) == 1


def test_a_mode_checked_for_emptiness_passes() -> None:
    assert empty_mode_violations(ast.parse(GUARDED)) == []
