from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from borges.analysis.harness import parse_error, parse_output, render_step
from borges.analysis.harness_result_checks import MODEL_ROWS_NOTE
from borges.analysis.models import Option, Step

CODE = """
import statsmodels.formula.api as smf


def estimate(df, ctx):
    df = df.copy()
    OUTCOME
    fit = smf.ols("y ~ x + c", data=df).fit()
    return {"estimate": float(fit.params["x"]), "ci_low": float(fit.conf_int().loc["x", 0]),
            "ci_high": float(fit.conf_int().loc["x", 1]), "p_value": float(fit.pvalues["x"]),
            "n": int(df["y"].notna().sum())}
"""
RAW = CODE.replace("OUTCOME", "pass")
SCALED = CODE.replace("OUTCOME", 'df["y"] = (df["y"] - df["y"].mean()) / df["y"].std()')


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    rng = np.random.default_rng(3)
    frame = pd.DataFrame({"x": rng.normal(size=200), "c": rng.normal(size=200)})
    frame["y"] = 2 * frame["x"] + rng.normal(scale=3, size=200)
    frame.loc[:9, "c"] = np.nan
    frame.to_parquet(tmp_path / "data.parquet")
    return tmp_path


def run(workdir: Path, code: str, standardised: bool) -> subprocess.CompletedProcess:
    option = Option(id="o", label="l", rationale="r", spec="s", is_default=True, code=code)
    step = Step(id="model", title="t", kind="model", description="d", options=[option])
    path = workdir / "step.py"
    path.write_text(render_step(step, option, standardised=standardised))
    return subprocess.run(
        [sys.executable, str(path)], cwd=workdir, capture_output=True, text=True, timeout=120
    )


def test_a_raw_outcome_fails_under_a_standardised_rule(workdir: Path) -> None:
    done = run(workdir, RAW, standardised=True)
    assert done.returncode == 1
    error = parse_error(done.stdout)
    assert error is not None and "reads a standardised coefficient" in error
    assert "'y' has standard deviation" in error


def test_a_raw_outcome_passes_when_the_rule_is_not_standardised(workdir: Path) -> None:
    assert run(workdir, RAW, standardised=False).returncode == 0


def test_n_is_the_rows_the_model_was_fitted_on(workdir: Path) -> None:
    done = run(workdir, SCALED, standardised=True)
    assert done.returncode == 0, done.stdout
    traces, result = parse_output(done.stdout)
    assert result is not None and result.n == 190
    assert MODEL_ROWS_NOTE in traces[-1].note


PER_USER = """
import statsmodels.formula.api as smf


def estimate(df, ctx):
    data = DATA
    fit = smf.ols("revenue_u ~ treated", data=data).fit()
    return {"estimate": float(fit.params["treated"]),
            "ci_low": float(fit.conf_int().loc["treated", 0]),
            "ci_high": float(fit.conf_int().loc["treated", 1]),
            "p_value": float(fit.pvalues["treated"]), "n": int(len(data))}
"""


def sessions(workdir: Path) -> None:
    rng = np.random.default_rng(5)
    users = pd.DataFrame({"user_id": range(300), "treated": rng.integers(0, 2, 300)})
    users["revenue_u"] = rng.exponential(10, 300) + users["treated"]
    rows = users.loc[users.index.repeat(rng.integers(1, 4, 300))].reset_index(drop=True)
    rows["session_id"] = range(len(rows))
    rows.to_parquet(workdir / "data.parquet")


def test_user_totals_copied_onto_every_session_fail_the_model(workdir: Path) -> None:
    sessions(workdir)
    done = run(workdir, PER_USER.replace("DATA", "df"), standardised=False)
    assert done.returncode == 1
    error = parse_error(done.stdout)
    assert error is not None and "for 300 distinct 'user_id' values" in error
    assert "drop_duplicates('user_id')" in error


def test_one_row_per_user_passes(workdir: Path) -> None:
    sessions(workdir)
    code = PER_USER.replace("DATA", "df.drop_duplicates('user_id')")
    assert run(workdir, code, standardised=False).returncode == 0
