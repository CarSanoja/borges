from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from borges.analysis.harness import parse_error, render_step
from borges.analysis.models import Option, Step

PROMISES_DUMMIES = (
    "def apply(df, ctx):\n"
    "    ctx['covariates'] = ['age'] + [f'country_{i}' for i in range(1, 3)]\n"
    "    return df\n"
)
NAMES_COLUMNS = "def apply(df, ctx):\n    ctx['covariates'] = ['age', 'country']\n    return df\n"


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    frame = pd.DataFrame({"age": [30, 40, 50], "country": [1, 2, 3], "y": [0.1, 0.2, 0.3]})
    frame.to_parquet(tmp_path / "data.parquet")
    return tmp_path


def run(workdir: Path, code: str) -> subprocess.CompletedProcess:
    option = Option(id="o", label="l", rationale="r", spec="s", is_default=True, code=code)
    step = Step(id="cov", title="t", kind="feature", description="d", options=[option])
    path = workdir / "step.py"
    path.write_text(render_step(step, option))
    return subprocess.run(
        [sys.executable, str(path)], cwd=workdir, capture_output=True, text=True, timeout=120
    )


def test_covariates_that_are_not_columns_fail_the_step(workdir: Path) -> None:
    done = run(workdir, PROMISES_DUMMIES)
    assert done.returncode == 1
    error = parse_error(done.stdout)
    assert error is not None and "['country_1', 'country_2']" in error
    assert "dummies of 'country'" in error


def test_covariates_that_are_columns_pass(workdir: Path) -> None:
    assert run(workdir, NAMES_COLUMNS).returncode == 0
