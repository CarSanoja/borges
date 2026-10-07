from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from borges.analysis.harness import parse_error, render_step
from borges.analysis.models import Option, Step

FILTER = """
def apply(df, ctx):
    return df[df["sure"] >= 4]
"""
FRESH_INDEX = """
import numpy as np
import pandas as pd


def apply(df, ctx):
    committed = pd.Series(np.zeros(len(df), dtype="int8"))
    committed[df["relationship"].isin([3, 4])] = 1
    df = df.copy()
    df["committed"] = committed
    return df
"""


def run(workdir: Path, step_id: str, kind: str, code: str) -> subprocess.CompletedProcess:
    option = Option(id="o", label="Option", rationale="r", spec="s", code=code)
    produces = ["committed"] if kind == "feature" else []
    step = Step(
        id=step_id, title=step_id, kind=kind, description="d", options=[option], produces=produces
    )
    (workdir / "step.py").write_text(render_step(step, option))
    return subprocess.run(
        [sys.executable, "step.py"], cwd=workdir, capture_output=True, text=True, timeout=120
    )


def test_a_step_after_a_filter_reads_a_contiguous_index(tmp_path: Path) -> None:
    """fertility_vote on 7 October: after a filter left gaps in the index, a step that built its
    indicator on a fresh 0..n-1 index failed in every universe with that filter."""
    frame = pd.DataFrame({"sure": [9, 2, 8, 1, 7, 9], "relationship": [1, 3, 4, 4, 3, 2]})
    (tmp_path / "state").mkdir()
    frame.to_parquet(tmp_path / "state" / "df.parquet")
    (tmp_path / "state" / "ctx.json").write_text(json.dumps({}))
    assert run(tmp_path, "filter", "filter", FILTER).returncode == 0
    done = run(tmp_path, "feature", "feature", FRESH_INDEX)
    assert parse_error(done.stdout) is None, done.stdout
    out = pd.read_parquet(tmp_path / "state" / "df.parquet")
    assert out["relationship"].tolist() == [1, 4, 3, 2]
    assert out["committed"].tolist() == [0, 1, 1, 0]
