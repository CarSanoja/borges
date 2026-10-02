from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from borges.analysis.harness import parse_error, parse_output, render_step
from borges.analysis.models import Option, Step

PROPORTIONS = """
import numpy as np


def estimate(df, ctx):
    a = df[df["arm"] == 1]["y"]
    b = df[df["arm"] == 0]["y"]
    p1, p0 = a.mean(), b.mean()
    se = np.sqrt(p1 * (1 - p1) / len(a) + p0 * (1 - p0) / len(b)) / SHRINK
    diff = float(p1 - p0)
    return {
        "estimate": diff,
        "ci_low": diff - 1.96 * se,
        "ci_high": diff + 1.96 * se,
        "p_value": 0.5,
        "n": len(df),
    }
"""

CLUSTERED = """
def estimate(df, ctx):
    diff = float(df[df["arm"] == 1]["y"].mean() - df[df["arm"] == 0]["y"].mean())
    return {
        "estimate": diff,
        "ci_low": diff - 0.15,
        "ci_high": diff + 0.15,
        "p_value": 0.5,
        "n": len(df),
    }
"""

RAISES_ON_HALF = """
def estimate(df, ctx):
    if len(df) < 1000:
        raise RuntimeError("needs the full data")
    return {"estimate": 0.0, "ci_low": -0.1, "ci_high": 0.1, "p_value": 0.5, "n": len(df)}
"""


def frame(rows: int = 4000) -> pd.DataFrame:
    rng = np.random.default_rng(3)
    arm = rng.integers(0, 2, rows)
    y = (rng.random(rows) < 0.3 + 0.0 * arm).astype(int)
    return pd.DataFrame({"arm": arm, "y": y})


def run(tmp_path: Path, code: str, data: pd.DataFrame, split_half: bool) -> tuple:
    option = Option(id="o", label="l", rationale="r", spec="s", is_default=True, code=code)
    step = Step(id="m", title="t", kind="model", description="d", options=[option])
    (tmp_path / "step.py").write_text(render_step(step, option, split_half=split_half))
    data.to_parquet(tmp_path / "data.parquet")
    done = subprocess.run(
        [sys.executable, "step.py"], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )
    return done, parse_error(done.stdout), parse_output(done.stdout)[1]


def test_correct_standard_error_passes(tmp_path: Path) -> None:
    done, error, result = run(tmp_path, PROPORTIONS.replace("SHRINK", "1.0"), frame(), True)
    assert done.returncode == 0 and error is None and result is not None


def test_standard_error_divided_by_root_n_again_fails(tmp_path: Path) -> None:
    code = PROPORTIONS.replace("SHRINK", "np.sqrt(len(df))")
    done, error, result = run(tmp_path, code, frame(), True)
    assert done.returncode == 1 and result is None
    assert error is not None and "far too narrow" in error and "statsmodels" in error


def test_the_same_code_is_not_checked_outside_smoke(tmp_path: Path) -> None:
    code = PROPORTIONS.replace("SHRINK", "np.sqrt(len(df))")
    done, error, result = run(tmp_path, code, frame(), False)
    assert done.returncode == 0 and result is not None


def test_wide_clustered_interval_passes(tmp_path: Path) -> None:
    done, _, result = run(tmp_path, CLUSTERED, frame(), True)
    assert done.returncode == 0 and result is not None


def test_interval_hundreds_of_times_too_wide_fails(tmp_path: Path) -> None:
    done, error, result = run(tmp_path, PROPORTIONS.replace("SHRINK", "(1 / 300)"), frame(), True)
    assert done.returncode == 1 and result is None
    assert error is not None and "far too wide" in error and "same scale" in error


def test_wide_threshold_has_no_false_alarms_for_a_five_fold_clustered_error() -> None:
    rng = np.random.default_rng(1)
    d = np.abs(rng.normal(0.0, 2.0, size=(20000, 4)))
    ratios = np.median(d, axis=1) / (2.0 * 5.0)
    assert float((ratios < 0.025).mean()) < 0.01


def test_estimate_raising_on_a_half_skips_the_check(tmp_path: Path) -> None:
    done, _, result = run(tmp_path, RAISES_ON_HALF, frame(), True)
    assert done.returncode == 0 and result is not None


def test_too_few_rows_skips_the_check(tmp_path: Path) -> None:
    code = PROPORTIONS.replace("SHRINK", "np.sqrt(len(df))")
    done, _, result = run(tmp_path, code, frame(30), True)
    assert done.returncode == 0 and result is not None


def test_threshold_has_no_false_alarms_for_a_correct_standard_error() -> None:
    rng = np.random.default_rng(0)
    trials = 20000
    d = np.abs(rng.normal(0.0, 2.0, size=(trials, 4)))
    ratios = np.median(d, axis=1) / 2.0
    assert float(ratios.max()) < 6.0
    assert float(np.median(ratios)) == pytest.approx(0.70, abs=0.03)


def test_injected_check_only_when_requested() -> None:
    option = Option(id="o", label="l", rationale="r", spec="s", is_default=True, code=CLUSTERED)
    step = Step(id="m", title="t", kind="model", description="d", options=[option])
    assert "if True:" not in render_step(step, option)
    assert "_check_split_half(df, ctx, result)" in render_step(step, option)
