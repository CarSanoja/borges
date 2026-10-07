from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from borges.analysis.harness import parse_error, render_step
from borges.analysis.models import Option, Step

FIRST = """
def apply(df, ctx):
    df = df.copy()
    df["cycle_day"] = (28 - (df["next"] - df["tested"]).dt.days).clip(1, 28)
    df.loc[df["id"] == 2, "cycle_day"] = 11
    return df
"""
RECOMPUTES = """
def apply(df, ctx):
    df = df.copy()
    df["cycle_day"] = (28 - (df["next"] - df["tested"]).dt.days).clip(1, 28)
    df["high"] = df["cycle_day"].between(7, 14).astype(int)
    return df
"""
READS = """
def apply(df, ctx):
    df = df.copy()
    df["high"] = df["cycle_day"].between(7, 14).astype(int)
    return df
"""
RECODES_RAW = """
def apply(df, ctx):
    df = df.copy()
    df["id"] = 0
    df["high"] = df["cycle_day"].between(7, 14).astype(int)
    return df
"""


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    tested = pd.Timestamp("2012-10-01")
    frame = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "tested": [tested] * 3,
            "next": [tested + pd.Timedelta(days=d) for d in (5, 0, 20)],
        }
    )
    frame.loc[1, "next"] = pd.NaT
    frame.to_parquet(tmp_path / "data.parquet")
    return tmp_path


def run(workdir: Path, code: str, produces: list[str]) -> subprocess.CompletedProcess:
    option = Option(id="o", label="Option", rationale="r", spec="s", code=code)
    step = Step(
        id="s", title="Step", kind="transform", description="d", options=[option], produces=produces
    )
    (workdir / "step.py").write_text(render_step(step, option))
    return subprocess.run(
        [sys.executable, "step.py"], cwd=workdir, capture_output=True, text=True, timeout=120
    )


def second(workdir: Path, code: str, produces: list[str]) -> str | None:
    assert run(workdir, FIRST, ["cycle_day"]).returncode == 0
    (workdir / "state" / "ctx.json").write_text(json.dumps({}))
    return parse_error(run(workdir, code, produces).stdout)


def test_a_step_that_recomputes_an_earlier_column_is_refused(workdir: Path) -> None:
    error = second(workdir, RECOMPUTES, ["high"])
    assert error is not None and "computes 'cycle_day' from scratch" in error
    assert "Read df['cycle_day'] as it arrives" in error


def test_a_step_that_reads_the_earlier_column_keeps_the_hand_set_row(workdir: Path) -> None:
    assert second(workdir, READS, ["high"]) is None
    out = pd.read_parquet(workdir / "state" / "df.parquet")
    assert out["cycle_day"].tolist() == [23, 11, 8]


def test_a_step_that_declares_the_column_may_rebuild_it(workdir: Path) -> None:
    assert second(workdir, RECOMPUTES, ["high", "cycle_day"]) is None


def test_overwriting_a_raw_column_is_not_this_check(workdir: Path) -> None:
    assert second(workdir, RECODES_RAW, ["high"]) is None
