from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from borges.analysis.harness import parse_error, render_step
from borges.analysis.models import Option, Step

INTERACTION = """
import statsmodels.api as sm

def estimate(df, ctx):
    d = df.assign(both=df["high"] * df["committed"])
    fit = sm.OLS(d["rel"], sm.add_constant(d[["high", "committed", "both"]])).fit(cov_type="HC3")
    low, high = fit.conf_int().loc["both"]
    return {"estimate": float(fit.params["both"]), "ci_low": float(low), "ci_high": float(high),
            "p_value": float(fit.pvalues["both"]), "n": int(len(d))}
"""
MAIN_EFFECT = """
import statsmodels.api as sm

def estimate(df, ctx):
    fit = sm.OLS(df["rel"], sm.add_constant(df[["high", "age"]])).fit(cov_type="HC3")
    low, high = fit.conf_int().loc["high"]
    return {"estimate": float(fit.params["high"]), "ci_low": float(low), "ci_high": float(high),
            "p_value": float(fit.pvalues["high"]), "n": int(len(df))}
"""


def frame(single_high: int) -> pd.DataFrame:
    rng = np.random.default_rng(5)
    sizes = {(0, 0): 40, (0, 1): 90, (1, 0): single_high, (1, 1): 25}
    rows = [(h, c) for (h, c), k in sizes.items() for _ in range(k)]
    data = pd.DataFrame(rows, columns=["high", "committed"]).astype(float)
    data["rel"] = rng.normal(5, 2, len(data))
    data["age"] = rng.normal(30, 5, len(data))
    return data


def run(tmp_path: Path, data: pd.DataFrame, code: str, full_data_checks: bool):
    (tmp_path / "state").mkdir(exist_ok=True)
    data.to_parquet(tmp_path / "state" / "df.parquet")
    (tmp_path / "state" / "ctx.json").write_text(json.dumps({}))
    option = Option(id="m", label="OLS", rationale="r", spec="OLS with HC3.", code=code)
    step = Step(id="s", title="Model", kind="model", description="d", options=[option])
    (tmp_path / "step.py").write_text(render_step(step, option, full_data_checks=full_data_checks))
    return subprocess.run(
        [sys.executable, "step.py"], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )


def test_an_interaction_cell_of_two_rows_fails_the_universe(tmp_path: Path) -> None:
    done = run(tmp_path, frame(2), INTERACTION, full_data_checks=True)
    assert done.returncode != 0
    error = parse_error(done.stdout) or ""
    assert "group of only 2 rows" in error and "[40, 90, 2, 25]" in error


def test_the_smoke_run_and_reproduce_do_not_apply_it(tmp_path: Path) -> None:
    done = run(tmp_path, frame(2), INTERACTION, full_data_checks=False)
    assert done.returncode == 0, done.stdout + done.stderr


@pytest.mark.parametrize("single_high", [5, 30])
def test_cells_of_five_rows_or_more_pass(tmp_path: Path, single_high: int) -> None:
    done = run(tmp_path, frame(single_high), INTERACTION, full_data_checks=True)
    assert done.returncode == 0, done.stdout + done.stderr


def test_a_binary_exposure_counts_its_two_levels(tmp_path: Path) -> None:
    data = frame(2)
    data.loc[data.index[:-3], "high"] = 0.0
    done = run(tmp_path, data, MAIN_EFFECT, full_data_checks=True)
    assert "group of only 3 rows" in (parse_error(done.stdout) or "")
    data.loc[data.index[:60], "high"] = 1.0
    assert run(tmp_path, data, MAIN_EFFECT, full_data_checks=True).returncode == 0
