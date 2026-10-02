from __future__ import annotations

from borges.analysis.harness import parse_error
from tests.analysis.test_harness import make_step, run, workdir  # noqa: F401

STORES_FRAME = """
def apply(df, ctx):
    ctx["kept"] = df
    return df
"""

STORES_NAMES = """
def apply(df, ctx):
    ctx["kept"] = list(df.columns)
    return df
"""


def test_frame_in_ctx_names_the_key_and_the_fix(workdir) -> None:  # noqa: F811
    step, option = make_step("s1", "filter", STORES_FRAME)
    proc = run(workdir, step, option)
    error = parse_error(proc.stdout) or ""
    assert proc.returncode != 0
    assert "ctx['kept'] holds a DataFrame" in error
    assert "keep only column names or numbers in ctx" in error


def test_json_values_in_ctx_are_kept(workdir) -> None:  # noqa: F811
    step, option = make_step("s1", "filter", STORES_NAMES)
    proc = run(workdir, step, option)
    assert proc.returncode == 0, proc.stdout
    assert parse_error(proc.stdout) is None
