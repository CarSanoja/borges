from __future__ import annotations

from borges.analysis.code_guard import check_code
from borges.analysis.prompts.coder import SYSTEM

ASSIGN_IDIOM = """
def apply(df, ctx):
    names = ["a", "b"]
    return df.assign(**{name + "_z": (df[name] - df[name].mean()) for name in names})
"""

FRAME_IDIOM = """
def apply(df, ctx):
    for col in ["a"]:
        df[col + "_z"] = df[col] - df[col].mean()
    return df
"""

REJECTED_IDIOM = """
def apply(df, ctx):
    values = {}
    for col in ["a"]:
        values[col + "_z"] = 1
    return df
"""


def test_prompt_warns_against_computed_subscript_keys() -> None:
    assert "df[col + " in SYSTEM
    assert "df.assign(**{name: values})" in SYSTEM


def test_the_advertised_alternative_passes_the_guard() -> None:
    assert check_code(ASSIGN_IDIOM, "transform") == []
    assert check_code(FRAME_IDIOM, "transform") == []
    assert any("computed string key" in v for v in check_code(REJECTED_IDIOM, "transform"))
