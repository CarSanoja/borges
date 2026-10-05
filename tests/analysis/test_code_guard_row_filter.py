from __future__ import annotations

import pytest

from borges.analysis.code_guard_row_filter import row_filter_violations

WINSORIZE_SPEC = (
    "For each column in ['balance', 'duration', 'campaign', 'pdays', 'previous'], compute 1st "
    "and 99th percentiles, clip values below/above to these percentiles; return DataFrame with "
    "updated columns; no columns written to ctx."
)
WINSORIZE = """def apply(df, ctx):
    df = df.copy()
    df = df[df['contact'].notna()]
    df = df[df['pdays'] >= 0]
    for col in ['balance', 'duration']:
        df[col] = df[col].clip(df[col].quantile(0.01), df[col].quantile(0.99))
    return df
"""


def test_the_bank_winsorizing_option_that_dropped_rows_is_flagged() -> None:
    found = row_filter_violations(WINSORIZE, WINSORIZE_SPEC)
    assert [f.split(":")[0] for f in found] == ["line 3", "line 4"]


@pytest.mark.parametrize(
    "line",
    [
        "out = df.dropna(subset=['contact'])",
        "out = df.loc[(df['games'] <= 10) & (df['x'] > 0), ['games']]",
        "out = df.query('games > 0').copy()",
    ],
)
def test_other_row_removals_in_a_returned_frame_are_flagged(line: str) -> None:
    code = f"def apply(df, ctx):\n    {line}\n    return out\n"
    assert row_filter_violations(code, "Cap games at its 95th percentile.")


@pytest.mark.parametrize(
    "spec",
    [
        "Exclude internal sessions.",
        "Keep only rows with valid ratings.",
        "df = df[~df['is_internal']].copy(); return df",
    ],
)
def test_a_spec_that_removes_rows_allows_it(spec: str) -> None:
    code = "def apply(df, ctx):\n    df = df[~df['is_internal']].copy()\n    return df\n"
    assert row_filter_violations(code, spec) == []


def test_a_mask_used_for_a_statistic_is_not_a_removal() -> None:
    code = (
        "def apply(df, ctx):\n    cap = df[df['games'] > 0]['games'].quantile(0.95)\n"
        "    df['games'] = df['games'].clip(upper=cap)\n    return df\n"
    )
    assert row_filter_violations(code, "Cap games at the 95th percentile of positive games.") == []


SCALE = """import pandas as pd


def apply(df, ctx):
    out = df.copy()
    columns = [c for c in ("wb", "rel", "norm") if c in out.columns]
    out = out.dropna(subset=columns)
    out["y"] = (out["wb"] - out["wb"].mean()) / out["wb"].std()
    out["x"] = (out["rel"] - out["rel"].mean()) / out["rel"].std()
    if "norm" in out.columns:
        out["m"] = (out["norm"] - out["norm"].mean()) / out["norm"].std()
    return out
"""


def test_dropping_rows_missing_a_transformed_value_is_allowed() -> None:
    assert row_filter_violations(SCALE, "y, x (and m) = global z-scores.") == []


def test_dropping_rows_missing_an_untouched_value_is_flagged() -> None:
    code = SCALE.replace('("wb", "rel", "norm")', '("wb", "rel", "contact")')
    assert row_filter_violations(code, "y, x (and m) = global z-scores.")


def test_dropping_rows_missing_a_value_transformed_in_a_loop_is_allowed() -> None:
    code = """import pandas as pd


def apply(df, ctx):
    out = df.dropna(subset=["wb", "rel"])
    for source, target in (("wb", "y"), ("rel", "x")):
        centred = out[source] - out.groupby("country")[source].transform("mean")
        out[target] = centred / centred.std()
    return out
"""
    assert row_filter_violations(code, "y and x centred on their country mean and scaled.") == []
