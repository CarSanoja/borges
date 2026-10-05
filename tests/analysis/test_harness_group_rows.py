from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from borges.analysis.harness import parse_error, render_step
from borges.analysis.keep_intent import grouped_by
from borges.analysis.models import Option, Step

ONE_GROUP = """
import pandas as pd

def apply(df, ctx):
    out = pd.DataFrame({"user_id": [df["user_id"].iloc[0]], "variant": [df["variant"].iloc[0]],
                        "converted_user": [df["converted"].max()]})
    return out
"""
GROUPED = """
def apply(df, ctx):
    out = df.groupby("user_id", as_index=False).agg(
        variant=("variant", "first"), converted_user=("converted", "max"))
    return out
"""
MERGED = """
def apply(df, ctx):
    out = df.copy()
    out["user_rate"] = out.groupby("user_id")["converted"].transform("mean")
    return out
"""
SPEC = "Group by user_id; compute variant as the first variant per user and converted_user as max."


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    frame = pd.DataFrame(
        {
            "user_id": [1, 1, 2, 3, 3, 3],
            "variant": ["treatment", "treatment", "control", "control", "control", "control"],
            "converted": [0, 1, 0, 1, 0, 0],
        }
    )
    (tmp_path / "state").mkdir()
    frame.to_parquet(tmp_path / "state" / "df.parquet")
    (tmp_path / "state" / "ctx.json").write_text(json.dumps({}))
    return tmp_path


def run(workdir: Path, code: str) -> subprocess.CompletedProcess:
    option = Option(id="g", label="User level", rationale="r", spec=SPEC, code=code)
    step = Step(id="a", title="Aggregate", kind="transform", description="d", options=[option])
    (workdir / "step.py").write_text(render_step(step, option))
    return subprocess.run(
        [sys.executable, "step.py"], cwd=workdir, capture_output=True, text=True, timeout=120
    )


def test_an_aggregation_coded_for_one_group_fails(workdir: Path) -> None:
    error = parse_error(run(workdir, ONE_GROUP).stdout)
    assert error is not None and "has 3 distinct values, but its code returns 1 rows" in error


@pytest.mark.parametrize("code", [GROUPED, MERGED])
def test_an_aggregation_or_a_group_column_passes(workdir: Path, code: str) -> None:
    done = run(workdir, code)
    assert done.returncode == 0, done.stdout


@pytest.mark.parametrize(
    ("kind", "spec", "key"),
    [
        ("transform", "Group by user_id; take the max of converted.", "user_id"),
        ("feature", "Mean rating grouped by `playerShort`.", "playerShort"),
        ("filter", "Group by user_id and drop users with one session.", None),
        ("transform", "Standardise the outcome.", None),
    ],
)
def test_the_group_key_is_read_from_the_option(kind: str, spec: str, key: str | None) -> None:
    option = Option(id="o", label="l", rationale="r", spec=spec)
    step = Step(id="s", title="t", kind=kind, description="d", options=[option])
    assert grouped_by(step, option) == key
