from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from borges.analysis.harness import parse_error, parse_output, render_step
from borges.analysis.models import Option, Step

RUN_38 = """
def apply(df, ctx):
    df = df.copy()
    cycle_day = (28 - df['days_to_next']).clip(lower=1, upper=28)
    df.loc[[15, 16], 'cycle_day'] = [11, 18]
    mask = cycle_day.between(7, 14) | cycle_day.between(17, 25)
    return df[mask].reset_index(drop=True)
"""
WHOLE = RUN_38.replace(
    "    df.loc[[15, 16], 'cycle_day'] = [11, 18]",
    "    df['cycle_day'] = cycle_day\n    df.loc[[15, 16], 'cycle_day'] = [11, 18]",
)


def run(tmp_path: Path, code: str) -> subprocess.CompletedProcess:
    option = Option(id="o", label="l", rationale="r", spec="s", is_default=True, code=code)
    step = Step(
        id="days",
        title="t",
        kind="filter",
        description="d",
        options=[option],
        produces=["cycle_day"],
    )
    frame = pd.DataFrame({"days_to_next": np.arange(200) % 30, "x": np.arange(200)})
    (tmp_path / "state").mkdir()
    frame.to_parquet(tmp_path / "state" / "df.parquet")
    (tmp_path / "state" / "ctx.json").write_text(json.dumps({}))
    (tmp_path / "step.py").write_text(render_step(step, option))
    return subprocess.run(
        [sys.executable, "step.py"], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )


def test_a_produced_column_missing_in_almost_every_kept_row_fails_the_step(tmp_path: Path) -> None:
    """fertility_vote on 7 October, run 38: cycle_day existed, and was missing in 300 of 301
    rows."""
    error = parse_error(run(tmp_path, RUN_38).stdout)
    assert error is not None and "this step must produce 'cycle_day' with a value" in error


def test_a_computed_column_with_rows_set_by_hand_on_top_passes(tmp_path: Path) -> None:
    traces, _ = parse_output(run(tmp_path, WHOLE).stdout)
    assert traces and traces[-1].rows_after > 20
