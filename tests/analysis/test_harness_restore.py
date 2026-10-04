from __future__ import annotations

from pathlib import Path

import pandas as pd

from tests.analysis.test_harness_effects import make, run

ONE_HOT = """
import pandas as pd


def apply(df, ctx):
    return pd.get_dummies(df, columns=["variant"], drop_first=True, dtype=float)
"""
FILTER_KEEPS_LABELS = """
def apply(df, ctx):
    return df[df["x"] > 0].drop(columns=["variant"])
"""
FILTER_RESETS = """
def apply(df, ctx):
    return df[df["x"] > 0].reset_index(drop=True)[["z"]]
"""


def test_a_one_hot_step_that_drops_the_original_keeps_it(tmp_path: Path) -> None:
    done, error, traces = run(tmp_path, *make("transform", ONE_HOT, []))
    assert done.returncode == 0, error
    assert "variant" in pd.read_parquet(tmp_path / "state" / "df.parquet").columns
    assert traces[0].note.startswith("columns the step dropped were kept from its input: variant")


def test_a_filter_that_keeps_row_labels_keeps_the_dropped_column(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("filter", FILTER_KEEPS_LABELS, []))
    assert done.returncode == 0, error


def test_a_filter_that_resets_and_reorders_rows_is_still_refused(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("filter", FILTER_RESETS, []))
    assert done.returncode == 1 and "apply() dropped the columns ['variant', 'x']" in error
