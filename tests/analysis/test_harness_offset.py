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
from borges.analysis.offset_intent import wants_offset

POISSON = """
import numpy as np
import statsmodels.api as sm

def estimate(df, ctx):
    model = sm.GLM(df["y"], sm.add_constant(df[["x"]]), family=sm.families.Poisson()__OFFSET__)
    fit = model.fit()
    low, high = fit.conf_int().loc["x"]
    return {"estimate": float(np.exp(fit.params["x"])), "ci_low": float(np.exp(low)),
            "ci_high": float(np.exp(high)), "p_value": float(fit.pvalues["x"]), "n": int(fit.nobs)}
"""


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    rng = np.random.default_rng(0)
    games = rng.integers(1, 20, size=300)
    x = rng.normal(size=300)
    frame = pd.DataFrame({"x": x, "games": games, "y": rng.poisson(0.1 * games * np.exp(0.2 * x))})
    (tmp_path / "state").mkdir()
    frame.to_parquet(tmp_path / "state" / "df.parquet")
    (tmp_path / "state" / "ctx.json").write_text(json.dumps({}))
    return tmp_path


def run(workdir: Path, code: str, spec: str) -> subprocess.CompletedProcess:
    option = Option(id="o", label="Poisson", rationale="r", spec=spec, is_default=True, code=code)
    step = Step(id="m", title="t", kind="model", description="d", options=[option])
    path = workdir / "step.py"
    path.write_text(render_step(step, option))
    return subprocess.run(
        [sys.executable, str(path)], cwd=workdir, capture_output=True, text=True, timeout=120
    )


SPEC = "Fit a Poisson GLM of y on x with offset=np.log(games)."


def test_a_model_that_drops_the_offset_its_spec_names_fails(workdir: Path) -> None:
    error = parse_error(run(workdir, POISSON.replace("__OFFSET__", ""), SPEC).stdout)
    assert error is not None and "the option's spec fits an offset" in error


def test_a_model_with_the_offset_passes(workdir: Path) -> None:
    code = POISSON.replace("__OFFSET__", ', offset=np.log(df["games"])')
    done = run(workdir, code, SPEC)
    assert done.returncode == 0, done.stdout


@pytest.mark.parametrize(
    ("spec", "wanted"),
    [
        (SPEC, True),
        ("Poisson GLM with exposure=games.", True),
        ("Poisson GLM without an offset.", False),
        ("Logistic regression of any red card.", False),
    ],
)
def test_the_offset_intent_is_read_from_the_spec(spec: str, wanted: bool) -> None:
    option = Option(id="o", label="Poisson", rationale="r", spec=spec, is_default=True)
    assert wants_offset(option) is wanted
