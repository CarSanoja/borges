from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from borges.analysis.harness import parse_error, parse_output, render_step
from borges.analysis.models import Option, Step

HEADER = """
import statsmodels.api as sm


def estimate(df, ctx):
    df = df.copy()
    df["xm"] = df["x"] * df["m"]
"""
RETURN = """
    return {"estimate": float(fit.params["xm"]), "ci_low": float(fit.conf_int().loc["xm", 0]),
            "ci_high": float(fit.conf_int().loc["xm", 1]), "p_value": float(fit.pvalues["xm"]),
            "n": int(fit.nobs)}
"""
ONLY_PRODUCT = HEADER + '    fit = sm.OLS(df["y"], sm.add_constant(df[["xm", "c"]])).fit()' + RETURN
WITH_MAIN = (
    HEADER + '    fit = sm.OLS(df["y"], sm.add_constant(df[["x", "m", "xm"]])).fit()' + RETURN
)


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    rng = np.random.default_rng(1)
    frame = pd.DataFrame({"x": rng.normal(size=200), "m": rng.normal(size=200)})
    frame["c"] = rng.normal(size=200)
    frame["y"] = frame["x"] + frame["m"] + 0.3 * frame["x"] * frame["m"] + rng.normal(size=200)
    frame = frame.astype({"x": "float32", "m": "float32"})
    frame.to_parquet(tmp_path / "data.parquet")
    return tmp_path


def run(workdir: Path, code: str) -> subprocess.CompletedProcess:
    option = Option(id="o", label="l", rationale="r", spec="s", is_default=True, code=code)
    step = Step(id="model", title="t", kind="model", description="d", options=[option])
    path = workdir / "step.py"
    path.write_text(render_step(step, option))
    return subprocess.run(
        [sys.executable, str(path)], cwd=workdir, capture_output=True, text=True, timeout=120
    )


def test_an_interaction_without_its_main_effects_fails_the_step(workdir: Path) -> None:
    done = run(workdir, ONLY_PRODUCT)
    assert done.returncode == 1
    error = parse_error(done.stdout)
    assert error is not None and "the interaction x x m" in error
    assert "leaves out x, m" in error


def test_an_interaction_with_its_main_effects_passes(workdir: Path) -> None:
    done = run(workdir, WITH_MAIN)
    assert done.returncode == 0, done.stdout
    _, result = parse_output(done.stdout)
    assert result is not None
