from __future__ import annotations

from pathlib import Path

from tests.analysis.test_harness_effects import make, run

DUMMIES = """
import pandas as pd


def apply(df, ctx):
    for col in ["variant", "z"]:
        dummies = pd.get_dummies(df[col].astype(str), prefix=col, drop_first=True, dtype=float)
        df = df.join(dummies)
    return df
"""


def test_a_one_level_column_may_have_no_dummies_under_a_glob(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("transform", DUMMIES, ["variant_*", "z_*"]))
    assert done.returncode == 0, error


def test_a_glob_of_a_column_with_levels_still_needs_its_dummies(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("transform", DUMMIES, ["variant_*", "x_*"]))
    assert done.returncode == 1 and error is not None
    assert "this step must produce 'x_*'" in error
