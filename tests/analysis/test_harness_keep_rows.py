from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from borges.analysis.harness import parse_error, render_step
from borges.analysis.keep_intent import keeps_rows
from borges.analysis.models import Option, Step

DROPS = """
def apply(df, ctx):
    out = df.copy()
    if ctx.get("keep_all", False):
        return out
    return out[out["is_internal"] == False]
"""
KEEPS = "def apply(df, ctx):\n    return df.copy()\n"
SPEC = "Return the input DataFrame unchanged; no rows are dropped."


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    frame = pd.DataFrame({"is_internal": [False, True, False, False], "y": [1, 0, 1, 0]})
    (tmp_path / "state").mkdir()
    frame.to_parquet(tmp_path / "state" / "df.parquet")
    (tmp_path / "state" / "ctx.json").write_text(json.dumps({}))
    return tmp_path


def run(workdir: Path, code: str) -> subprocess.CompletedProcess:
    option = Option(id="k", label="Keep all sessions", rationale="r", spec=SPEC, code=code)
    step = Step(id="f", title="Filter", kind="filter", description="d", options=[option])
    (workdir / "step.py").write_text(render_step(step, option))
    return subprocess.run(
        [sys.executable, "step.py"], cwd=workdir, capture_output=True, text=True, timeout=120
    )


def test_a_keep_all_option_that_drops_rows_fails(workdir: Path) -> None:
    error = parse_error(run(workdir, DROPS).stdout)
    assert error is not None and "says it keeps every row, but its code drops 1 of 4" in error


def test_a_keep_all_option_that_keeps_rows_passes(workdir: Path) -> None:
    done = run(workdir, KEEPS)
    assert done.returncode == 0, done.stdout


@pytest.mark.parametrize(
    ("kind", "label", "spec", "keeps"),
    [
        ("filter", "Keep all sessions", "Include every session.", True),
        ("filter", "Keep all records, no winsorizing", "Leave values as they are.", True),
        ("filter", "Keep all rows except tests", "Drop is_test rows.", False),
        ("feature", "Keep all covariates", "Use every column.", False),
        ("filter", "Exclude bots", "Drop rows with session_seconds < 10.", False),
    ],
)
def test_the_keep_intent_is_read_from_the_option(
    kind: str, label: str, spec: str, keeps: bool
) -> None:
    option = Option(id="o", label=label, rationale="r", spec=spec)
    step = Step(id="s", title="t", kind=kind, description="d", options=[option])
    assert keeps_rows(step, option) is keeps
