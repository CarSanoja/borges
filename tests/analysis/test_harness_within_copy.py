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
    df["hours_within"] = df["hours"] - df.groupby("manager")["hours"].transform("mean")
"""
RETURN = """
    return {"estimate": float(fit.params[TERM]), "ci_low": float(fit.conf_int().loc[TERM, 0]),
            "ci_high": float(fit.conf_int().loc[TERM, 1]), "p_value": float(fit.pvalues[TERM]),
            "n": int(fit.nobs)}
"""


def model(columns: list[str], term: str) -> str:
    fit = f'    fit = sm.OLS(df["y"], sm.add_constant(df[{columns!r}])).fit()'
    return HEADER + fit + RETURN.replace("TERM", repr(term))


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    rng = np.random.default_rng(3)
    manager = rng.integers(0, 30, 600)
    level = rng.normal(0, 3, 30)[manager]
    frame = pd.DataFrame({"manager": manager, "hours": level + rng.normal(10, 2, 600)})
    frame["mean_hours"] = frame.groupby("manager")["hours"].transform("mean")
    frame["y"] = 0.5 * level - 0.2 * frame["hours"] + rng.normal(size=600)
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


@pytest.mark.parametrize("term", ["hours", "hours_within"])
def test_an_exposure_beside_its_own_demeaned_copy_fails_the_step(workdir: Path, term: str) -> None:
    done = run(workdir, model(["hours", "hours_within"], term))
    error = parse_error(done.stdout)
    assert done.returncode == 1 and error is not None
    other = "hours" if term == "hours_within" else "hours_within"
    assert f"the model has both {term} and {other}," in error
    assert "not a fixed-effects estimate" in error


@pytest.mark.parametrize(
    ("columns", "term"), [(["hours_within"], "hours_within"), (["hours", "mean_hours"], "hours")]
)
def test_a_within_estimate_or_the_group_means_as_a_covariate_passes(
    workdir: Path, columns: list[str], term: str
) -> None:
    done = run(workdir, model(columns, term))
    assert done.returncode == 0, done.stdout
    _, result = parse_output(done.stdout)
    assert result is not None and result.estimate == pytest.approx(-0.2, abs=0.05)
