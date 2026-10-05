from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from borges.analysis.harness import parse_error, parse_output, render_step
from borges.analysis.models import Option, Step

CUT = """
def apply(df, ctx):
    out = df.copy()
    out["dark"] = (out["skin_tone"] >= 0.5).astype(int)
    return out
"""
KEPT_MISSING = CUT.replace(".astype(int)", '.astype(float).where(out["skin_tone"].notna())')
INDICATOR = CUT.replace(
    '(out["skin_tone"] >= 0.5).astype(int)', 'out["skin_tone"].isna().astype(int)'
)


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    rng = np.random.default_rng(0)
    tone = rng.choice([0.0, 0.25, 0.5, 0.75, 1.0], size=200)
    tone[:30] = np.nan
    frame = pd.DataFrame({"skin_tone": tone, "y": rng.poisson(1.0, size=200)})
    (tmp_path / "state").mkdir()
    frame.to_parquet(tmp_path / "state" / "df.parquet")
    (tmp_path / "state" / "ctx.json").write_text(json.dumps({}))
    return tmp_path


def run(workdir: Path, code: str, label: str = "Dark skin") -> subprocess.CompletedProcess:
    option = Option(id="o", label=label, rationale="r", spec="s", is_default=True, code=code)
    step = Step(id="tone", title="t", kind="transform", description="d", options=[option])
    path = workdir / "step.py"
    path.write_text(render_step(step, option))
    return subprocess.run(
        [sys.executable, str(path)], cwd=workdir, capture_output=True, text=True, timeout=120
    )


def test_a_cut_that_codes_missing_values_as_zero_fails_the_step(workdir: Path) -> None:
    done = run(workdir, CUT)
    error = parse_error(done.stdout)
    assert done.returncode == 1 and error is not None
    assert "'dark' is 0 on the 30 rows where 'skin_tone' is missing" in error


@pytest.mark.parametrize("code", [KEPT_MISSING, INDICATOR])
def test_a_cut_that_keeps_them_missing_or_a_missing_indicator_passes(
    workdir: Path, code: str
) -> None:
    done = run(workdir, code)
    traces, _ = parse_output(done.stdout)
    assert done.returncode == 0, done.stdout
    assert traces and traces[0].rows_after == 200


def test_a_fill_that_turns_missing_ratings_into_a_score_fails_unless_the_option_imputes(
    workdir: Path,
) -> None:
    filled = CUT.replace(
        'out["dark"] = (out["skin_tone"] >= 0.5).astype(int)',
        'out["tone"] = out["skin_tone"].fillna(0) * 2',
    )
    error = parse_error(run(workdir, filled).stdout)
    assert error is not None and "'tone' is 0.0 on the 30 rows" in error
    assert run(workdir, filled, label="Impute missing tones as 0").returncode == 0


def test_a_cut_at_a_numpy_threshold_over_missing_values_fails_as_constant(workdir: Path) -> None:
    code = CUT.replace(">= 0.5", '>= np.mean(out["skin_tone"].to_numpy())').replace(
        "def apply", "import numpy as np\n\n\ndef apply"
    )
    error = parse_error(run(workdir, code).stdout)
    assert error is not None and "'dark' has the same value in every row" in error


def test_a_constant_column_that_is_not_a_cut_passes(workdir: Path) -> None:
    code = CUT.replace('(out["skin_tone"] >= 0.5).astype(int)', "1.0")
    assert run(workdir, code).returncode == 0


def test_the_error_names_the_line_that_blanks_the_missing_rows(workdir: Path) -> None:
    error = parse_error(run(workdir, CUT).stdout)
    assert error is not None
    assert "out.loc[out[['skin_tone']].isna().all(axis=1), 'dark'] = float('nan')" in error


MODEL_CUT = """
import numpy as np
import statsmodels.api as sm

def estimate(df, ctx):
    data = df.copy()
    data["dark"] = (data["skin_tone"] >= 0.5).astype(int)
    fit = sm.GLM(data["y"], sm.add_constant(data[["dark"]]), family=sm.families.Poisson()).fit()
    low, high = fit.conf_int().loc["dark"]
    return {"estimate": float(fit.params["dark"]), "ci_low": float(low), "ci_high": float(high),
            "p_value": float(fit.pvalues["dark"]), "n": int(fit.nobs)}
"""


def run_model(workdir: Path, code: str) -> subprocess.CompletedProcess:
    option = Option(id="o", label="Poisson", rationale="r", spec="s", is_default=True, code=code)
    step = Step(id="m", title="t", kind="model", description="d", options=[option])
    path = workdir / "step.py"
    path.write_text(render_step(step, option))
    return subprocess.run(
        [sys.executable, str(path)], cwd=workdir, capture_output=True, text=True, timeout=120
    )


def test_a_model_that_cuts_a_column_with_missing_values_fails(workdir: Path) -> None:
    error = parse_error(run_model(workdir, MODEL_CUT).stdout)
    assert error is not None
    assert "the model reports n = 200, more than the 170 rows where 'skin_tone'" in error


def test_a_model_that_drops_the_missing_rows_first_passes(workdir: Path) -> None:
    code = MODEL_CUT.replace("data = df.copy()", 'data = df.dropna(subset=["skin_tone"]).copy()')
    done = run_model(workdir, code)
    assert done.returncode == 0, done.stdout
