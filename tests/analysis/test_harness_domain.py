from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from tests.analysis.test_harness_effects import make, run

LOG_OF_NEGATIVES = """
import numpy as np


def apply(df, ctx):
    out = df.copy()
    out["log_x"] = np.log1p(out["x"] - 2.0)
    return out
"""
SIGNED_LOG = """
import numpy as np


def apply(df, ctx):
    out = df.copy()
    out["log_x"] = np.arcsinh(out["x"] - 2.0)
    return out
"""
COERCES = """
import pandas as pd


def apply(df, ctx):
    out = df.copy()
    out["code"] = pd.to_numeric(out["variant"].where(out["x"] > 0, "n/a"), errors="coerce")
    return out
"""


def test_a_log_of_values_below_its_domain_is_refused_with_the_cause(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("transform", LOG_OF_NEGATIVES, ["log_x"]))
    assert done.returncode == 1
    assert error is not None and "turned 2 of 400 values of 'log_x' into NaN or infinity" in error
    assert "np.arcsinh" in error


def test_a_transform_defined_everywhere_passes(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("transform", SIGNED_LOG, ["log_x"]))
    assert done.returncode == 0, error
    out = pd.read_parquet(tmp_path / "state" / "df.parquet")
    assert np.isfinite(out["log_x"]).all()


def test_missing_values_made_without_a_numpy_domain_error_pass(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("transform", COERCES, ["code"]))
    assert done.returncode == 0, error
