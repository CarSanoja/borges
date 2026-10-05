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

FIT = """
import numpy as np
import statsmodels.api as sm

def estimate(df, ctx):
    x = sm.add_constant(df[["campaign", "age"]].astype(float))
    model = sm.GLM(df["y"].astype(float), x, family=sm.families.Binomial(){weights})
    fit = model.fit(cov_type="HC1")
    b, se = fit.params["campaign"], fit.bse["campaign"]
    return {{"estimate": float(np.exp(b)), "ci_low": float(np.exp(b - 1.96 * se)),
            "ci_high": float(np.exp(b + 1.96 * se)), "p_value": float(fit.pvalues["campaign"]),
            "n": int(len(df))}}
"""


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    rng = np.random.default_rng(3)
    campaign = rng.integers(1, 8, 600)
    frame = pd.DataFrame(
        {
            "campaign": campaign,
            "age": rng.normal(40, 10, 600),
            "survey_w": rng.uniform(0.5, 2.0, 600),
            "y": (rng.random(600) < 0.3 - 0.02 * campaign).astype(int),
        }
    )
    (tmp_path / "state").mkdir()
    frame.to_parquet(tmp_path / "state" / "df.parquet")
    (tmp_path / "state" / "ctx.json").write_text(json.dumps({}))
    return tmp_path


def run(workdir: Path, weights: str) -> subprocess.CompletedProcess:
    code = FIT.format(weights=weights)
    option = Option(id="m", label="Logit", rationale="r", spec="Logistic regression.", code=code)
    step = Step(id="s", title="Model", kind="model", description="d", options=[option])
    (workdir / "step.py").write_text(render_step(step, option))
    return subprocess.run(
        [sys.executable, "step.py"], cwd=workdir, capture_output=True, text=True, timeout=120
    )


@pytest.mark.parametrize(
    "weights", [', freq_weights=df["campaign"]', ', var_weights=df["campaign"]']
)
def test_a_model_weighted_by_its_exposure_fails(workdir: Path, weights: str) -> None:
    error = parse_error(run(workdir, weights).stdout)
    assert error is not None and "weights each row by the exposure itself" in error


@pytest.mark.parametrize("weights", ["", ', freq_weights=df["survey_w"]'])
def test_an_unweighted_or_design_weighted_model_passes(workdir: Path, weights: str) -> None:
    done = run(workdir, weights)
    assert done.returncode == 0, done.stdout
