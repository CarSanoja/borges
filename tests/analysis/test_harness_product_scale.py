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


def z(s):
    return (s - s.mean()) / s.std()


def estimate(df, ctx):
    df = df.copy()
    df["xz"], df["mz"] = z(df["x"]), z(df["m"])
"""
RETURN = """
    fit = sm.OLS(df["y"], sm.add_constant(df[MAIN + ["xm"]])).fit()
    return {"estimate": float(fit.params["xm"]), "ci_low": float(fit.conf_int().loc["xm", 0]),
            "ci_high": float(fit.conf_int().loc["xm", 1]), "p_value": float(fit.pvalues["xm"]),
            "n": int(fit.nobs)}
"""


def code(product: str, main: list[str]) -> str:
    return HEADER + f'    df["xm"] = {product}\n    MAIN = {main!r}' + RETURN


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    rng = np.random.default_rng(2)
    frame = pd.DataFrame({"x": rng.normal(3, 0.5, 300), "m": rng.normal(2, 0.3, 300)})
    frame["y"] = frame["x"] + frame["m"] + 0.4 * frame["x"] * frame["m"] + rng.normal(size=300)
    frame.to_parquet(tmp_path / "data.parquet")
    return tmp_path


def run(workdir: Path, source: str) -> subprocess.CompletedProcess:
    option = Option(id="o", label="l", rationale="r", spec="s", is_default=True, code=source)
    step = Step(id="model", title="t", kind="model", description="d", options=[option])
    path = workdir / "step.py"
    path.write_text(render_step(step, option))
    return subprocess.run(
        [sys.executable, str(path)], cwd=workdir, capture_output=True, text=True, timeout=120
    )


@pytest.mark.parametrize(
    ("product", "main"),
    [
        ('df["xz"] * df["mz"]', ["xz", "mz"]),
        ('df["x"] * df["m"]', ["x", "m"]),
        ('df["xz"] * df["mz"]', ["x", "m"]),
        ('(df["x"] - df["x"].mean()) * (df["m"] - df["m"].mean())', ["x", "m"]),
    ],
)
def test_a_product_on_the_scale_of_its_factors_passes(
    workdir: Path, product: str, main: list[str]
) -> None:
    done = run(workdir, code(product, main))
    assert done.returncode == 0, done.stdout
    assert parse_output(done.stdout)[1] is not None


def test_the_z_score_of_a_product_fails_the_step(workdir: Path) -> None:
    done = run(workdir, code('z(df["x"] * df["m"])', ["xz", "mz"]))
    assert done.returncode == 1
    error = parse_error(done.stdout)
    assert error is not None and "rescaled product of x and m" in error
    assert "product of the z-scores" in error
