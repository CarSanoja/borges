from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from borges.analysis.harness import parse_error, parse_output, render_step
from borges.analysis.harness_design import DESIGN_CONDITION_LIMIT
from borges.analysis.models import Option, Step

HEADER = """
import numpy as np
import pandas as pd
import statsmodels.api as sm


def estimate(df, ctx):
"""

COLLINEAR = (
    HEADER
    + """
    dummies = pd.get_dummies(df["month"], prefix="month", dtype=float)
    x = pd.concat([df[["x"]], dummies], axis=1)
    fit = sm.OLS(df["y"], sm.add_constant(x)).fit()
    return {"estimate": float(fit.params["x"]), "ci_low": float(fit.conf_int().loc["x", 0]),
            "ci_high": float(fit.conf_int().loc["x", 1]), "p_value": float(fit.pvalues["x"]),
            "n": int(fit.nobs)}
"""
)

FULL_RANK = COLLINEAR.replace("dtype=float)", "dtype=float, drop_first=True)")
ALIASED_ESTIMATE = (
    COLLINEAR.replace('params["x"]', 'params["month_jan"]')
    .replace('loc["x"', 'loc["month_jan"')
    .replace('pvalues["x"]', 'pvalues["month_jan"]')
)

NEAR_COLLINEAR = (
    HEADER
    + """
    x = pd.DataFrame({"a": df["x"], "b": df["x"] + 1e-13 * np.arange(len(df))})
    fit = sm.OLS(df["y"], sm.add_constant(x)).fit()
    return {"estimate": float(fit.params["a"]), "ci_low": -1.0, "ci_high": 1.0,
            "p_value": 0.5, "n": int(fit.nobs)}
"""
)

NO_STATSMODELS = """
def estimate(df, ctx):
    return {"estimate": 0.1, "ci_low": 0.0, "ci_high": 0.2, "p_value": 0.04, "n": len(df)}
"""


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    rng = np.random.default_rng(0)
    frame = pd.DataFrame(
        {
            "x": rng.normal(size=120),
            "month": ["jan", "feb", "mar", "apr"] * 30,
        }
    )
    frame["y"] = 0.5 * frame["x"] + rng.normal(size=120)
    frame.to_parquet(tmp_path / "data.parquet")
    return tmp_path


def run_model(workdir: Path, code: str, design_check: bool = True) -> subprocess.CompletedProcess:
    option = Option(id="o", label="l", rationale="r", spec="s", is_default=True, code=code)
    step = Step(id="model", title="t", kind="model", description="d", options=[option])
    path = workdir / "step.py"
    path.write_text(render_step(step, option, design_check=design_check))
    return subprocess.run(
        [sys.executable, str(path)], cwd=workdir, capture_output=True, text=True, timeout=120
    )


def test_rank_deficient_design_fails_the_step_with_a_clear_reason(workdir: Path) -> None:
    done = run_model(workdir, ALIASED_ESTIMATE)
    assert done.returncode == 1
    error = parse_error(done.stdout)
    assert error is not None and "rank-deficient or collinear" in error
    assert "rank 5 of 6 columns" in error
    assert "drop_first=True" in error


def test_full_rank_design_passes_and_records_its_terms(workdir: Path) -> None:
    done = run_model(workdir, FULL_RANK)
    assert done.returncode == 0, done.stdout
    traces, result = parse_output(done.stdout)
    assert result is not None
    design = traces[0].design
    assert design is not None and design["deficient"] is False
    assert design["rank"] == design["columns"] == 5
    assert design["terms"] == ["month", "x"]


def test_condition_number_above_the_limit_fails_the_step(workdir: Path) -> None:
    assert DESIGN_CONDITION_LIMIT == 1e10
    done = run_model(workdir, NEAR_COLLINEAR)
    assert done.returncode == 1
    assert "rank-deficient or collinear" in (parse_error(done.stdout) or "")


def test_check_can_be_switched_off_and_still_reports_the_deficiency(workdir: Path) -> None:
    done = run_model(workdir, ALIASED_ESTIMATE, design_check=False)
    assert done.returncode == 0, done.stdout
    traces, _ = parse_output(done.stdout)
    assert traces[0].design is not None and traces[0].design["deficient"] is True


def test_models_without_statsmodels_have_no_design_record(workdir: Path) -> None:
    done = run_model(workdir, NO_STATSMODELS)
    assert done.returncode == 0, done.stdout
    traces, _ = parse_output(done.stdout)
    assert traces[0].design is None


def test_filter_steps_carry_a_data_fingerprint(workdir: Path) -> None:
    code = "def apply(df, ctx):\n    return df[df['x'] > -9].copy()\n"
    alt = "def apply(df, ctx):\n    return df[df['x'] > 0].copy()\n"
    prints = []
    for body in (code, code, alt):
        option = Option(id="o", label="l", rationale="r", spec="s", is_default=True, code=body)
        step = Step(id="f", title="t", kind="filter", description="d", options=[option])
        path = workdir / "step.py"
        path.write_text(render_step(step, option))
        done = subprocess.run(
            [sys.executable, str(path)], cwd=workdir, capture_output=True, text=True, timeout=120
        )
        traces, _ = parse_output(done.stdout)
        prints.append(traces[0].fingerprint)
        (workdir / "state" / "df.parquet").unlink()
    assert prints[0] is not None and prints[0] == prints[1] != prints[2]


WIDE = (
    HEADER
    + """
    dummies = pd.get_dummies(df["player"], prefix="player", dtype=float)
    x = pd.concat([df[["x"]], dummies], axis=1)
    fit = sm.OLS(df["y"], sm.add_constant(x)).fit()
    return {"estimate": 0.0, "ci_low": -1.0, "ci_high": 1.0, "p_value": 0.5, "n": int(fit.nobs)}
"""
)


def test_a_design_of_hundreds_of_columns_names_the_identifier_cause(workdir: Path) -> None:
    rng = np.random.default_rng(1)
    rows = 1400
    frame = pd.DataFrame(
        {
            "x": rng.normal(size=rows),
            "y": rng.normal(size=rows),
            "player": [f"p{i % 700}" for i in range(rows)],
        }
    )
    frame.to_parquet(workdir / "data.parquet")
    done = run_model(workdir, WIDE)
    error = parse_error(done.stdout) or ""
    assert done.returncode == 1 and "702 columns" in error
    assert "cluster the errors on it or aggregate to that unit" in error


def test_a_narrow_deficient_design_does_not_carry_the_identifier_hint(workdir: Path) -> None:
    error = parse_error(run_model(workdir, ALIASED_ESTIMATE).stdout) or ""
    assert "rank-deficient or collinear" in error and "hundreds of levels" not in error
