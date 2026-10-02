from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from borges.analysis.harness import parse_error, parse_output, render_step
from borges.analysis.models import Option, Step

DROPS_COLUMN = """
def apply(df, ctx):
    return df.drop(columns=["z"])
"""

FITS_WITH_NAN = """
import statsmodels.api as sm

def estimate(df, ctx):
    X = sm.add_constant(df[["x"]])
    fit = sm.OLS(df["x"], X).fit()
    return {"estimate": 0.0, "ci_low": -1.0, "ci_high": 1.0, "p_value": 0.5, "n": len(df)}
"""

AGGREGATES = """
def apply(df, ctx):
    return df.groupby("variant", as_index=False).agg(x_mean=("x", "mean"))
"""

DROPS_CONTROL = """
def apply(df, ctx):
    return df[df["variant"] != "control"].reset_index(drop=True)
"""

ADDS_COLUMN = """
def apply(df, ctx):
    out = df.copy()
    out["score"] = out["x"] * 2.0
    out.loc[out.index[0], "x"] = 99.0
    ctx["added_note"] = "score"
    return out
"""

KEYS_ERROR = """
def estimate(df, ctx):
    return df["contact"].mean()
"""

READS_MISSING_ROWS = """
def apply(df, ctx):
    return df[["x"]]
"""

WRITES_ONLY_X = """
def apply(df, ctx):
    out = df.copy()
    out["x"] = 1.0
    return out
"""


def make(kind: str, code: str, produces: list[str] | None = None) -> tuple[Step, Option]:
    option = Option(id="o", label="l", rationale="r", spec="s", is_default=True, code=code)
    step = Step(
        id="s", title="t", kind=kind, description="d", options=[option], produces=produces or []
    )
    return step, option


def run(tmp_path: Path, step: Step, option: Option, smoke: bool = True):
    frame = pd.DataFrame(
        {
            "variant": ["control"] * 100 + ["treat"] * 300,
            "x": np.arange(400, dtype=float),
            "z": 1,
        }
    )
    frame.to_parquet(tmp_path / "data.parquet")
    (tmp_path / "step.py").write_text(render_step(step, option, split_half=smoke))
    done = subprocess.run(
        [sys.executable, "step.py"], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )
    return done, parse_error(done.stdout), parse_output(done.stdout)[0]


def test_transform_keeping_rows_cannot_drop_a_column(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("transform", DROPS_COLUMN))
    assert done.returncode == 1
    assert error is not None and "apply() dropped the columns ['z']" in error
    assert "never drop columns" in error


def test_filter_dropping_a_column_fails(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("filter", DROPS_COLUMN))
    assert done.returncode == 1
    assert error is not None and "apply() dropped the columns ['z']" in error


def test_aggregation_may_return_fewer_columns(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("transform", AGGREGATES))
    assert done.returncode == 0, error


def test_selecting_columns_fails(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("feature", READS_MISSING_ROWS))
    assert done.returncode == 1 and error is not None and "['variant', 'z']" in error


def test_missing_produced_name_fails(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("feature", WRITES_ONLY_X, ["wb_overall_mean"]))
    assert done.returncode == 1 and error is not None
    assert "this step must produce 'wb_overall_mean'" in error
    assert "Columns now: ['variant', 'x', 'z']" in error and "ctx keys: []" in error


def test_produced_name_in_ctx_or_column_passes(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("transform", ADDS_COLUMN, ["score", "added_note"]))
    assert done.returncode == 0 and error is None


def test_key_error_lists_columns_and_ctx(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("model", KEYS_ERROR))
    assert done.returncode == 1 and error is not None
    assert "'contact'" in error
    assert "columns available (3): ['variant', 'x', 'z']; ctx keys: []" in error


def test_filter_effects_show_the_dropped_group(tmp_path: Path) -> None:
    done, _, traces = run(tmp_path, *make("filter", DROPS_CONTROL))
    assert done.returncode == 0
    effects = traces[0].effects
    assert effects is not None
    assert effects["rows_before"] == 400 and effects["rows_after"] == 300
    assert effects["added"] == [] and effects["changed"] == []
    assert effects["dropped_rows_by"]["variant"] == {"control": 100}
    assert effects["dropped_rows_by"]["z"] == {"1": 100}


def test_transform_effects_have_a_bounded_probe(tmp_path: Path) -> None:
    done, _, traces = run(tmp_path, *make("transform", ADDS_COLUMN))
    assert done.returncode == 0
    effects = traces[0].effects
    assert effects is not None and "dropped_rows_by" not in effects
    assert effects["added"] == ["score"] and effects["changed"] == ["x"]
    assert effects["ctx_added"] == {"added_note": "'score'"}
    columns = effects["columns"]
    assert set(columns) == {"score", "x"}
    assert len(columns["score"]["probe"]) == 200
    assert columns["score"]["probe"]["3"] == 6.0
    assert columns["score"]["n_missing"] == 0 and columns["score"]["max"] == 798.0


def test_no_effects_outside_smoke(tmp_path: Path) -> None:
    done, _, traces = run(tmp_path, *make("transform", ADDS_COLUMN), smoke=False)
    assert done.returncode == 0 and traces[0].effects is None
    assert "effects" not in traces[0].model_dump(exclude_none=True)


@pytest.mark.parametrize("kind", ["filter", "feature"])
def test_effects_are_json_safe_with_non_finite_values(tmp_path: Path, kind: str) -> None:
    code = (
        "import numpy as np\n"
        "def apply(df, ctx):\n"
        "    out = df.copy()\n"
        "    out['r'] = np.where(out['x'] == 0, np.inf, out['x'])\n"
        "    return out\n"
    )
    done, _, traces = run(tmp_path, *make(kind, code))
    assert done.returncode == 0
    stats = traces[0].effects["columns"]["r"]
    assert stats["probe"]["0"] is None and stats["max"] is None


def test_missing_values_are_counted_when_a_fit_fails(tmp_path: Path) -> None:
    step, option = make("model", FITS_WITH_NAN)
    frame = pd.DataFrame({"x": [1.0, None, 3.0, 4.0] * 50})
    frame.to_parquet(tmp_path / "data.parquet")
    (tmp_path / "step.py").write_text(render_step(step, option))
    done = subprocess.run(
        [sys.executable, "step.py"], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )
    error = parse_error(done.stdout) or ""
    assert done.returncode == 1
    assert "missing values per column (200 rows): {'x': 50}" in error


DROPS_ARM = """
def apply(df, ctx):
    return df.groupby("user_id", as_index=False).agg(user_converted=("converted", "max"))
"""

READS_ARM = """
def estimate(df, ctx):
    lift = df.loc[df["variant"] == "t", "user_converted"].mean()
    return {"estimate": float(lift), "ci_low": -1.0, "ci_high": 2.0, "p_value": 0.5,
            "n": int(len(df))}
"""


def _sessions(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "user_id": np.repeat(np.arange(100), 3),
            "variant": np.repeat(np.where(np.arange(100) % 2 == 0, "t", "c"), 3),
            "converted": np.tile([0, 1, 0], 100),
        }
    )
    frame.to_parquet(tmp_path / "data.parquet")


def _execute(tmp_path: Path, kind: str, code: str) -> subprocess.CompletedProcess:
    step, option = make(kind, code)
    (tmp_path / "step.py").write_text(render_step(step, option))
    return subprocess.run(
        [sys.executable, "step.py"], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )


def test_aggregation_carries_attributes_constant_within_each_group(tmp_path: Path) -> None:
    _sessions(tmp_path)
    assert _execute(tmp_path, "transform", DROPS_ARM).returncode == 0
    out = pd.read_parquet(tmp_path / "state" / "df.parquet")
    assert list(out.columns) == ["user_id", "user_converted", "variant"]
    assert len(out) == 100
    done = _execute(tmp_path, "model", READS_ARM)
    assert done.returncode == 0, parse_error(done.stdout)


def test_aggregation_does_not_carry_columns_that_vary_within_a_group(tmp_path: Path) -> None:
    _sessions(tmp_path)
    assert _execute(tmp_path, "transform", DROPS_ARM).returncode == 0
    out = pd.read_parquet(tmp_path / "state" / "df.parquet")
    assert "converted" not in out.columns


UNSEEDED = """
import numpy as np

def estimate(df, ctx):
    draws = np.random.choice(len(df), size=len(df), replace=True)
    value = float(df["x"].to_numpy()[draws].mean())
    return {"estimate": value, "ci_low": value - 1.0, "ci_high": value + 1.0, "p_value": 0.5,
            "n": int(len(df))}
"""


def test_unseeded_randomness_is_reproducible(tmp_path: Path) -> None:
    pd.DataFrame({"x": np.arange(300, dtype=float)}).to_parquet(tmp_path / "data.parquet")
    outputs = [_execute(tmp_path, "model", UNSEEDED).stdout for _ in range(2)]
    assert parse_output(outputs[0])[1] == parse_output(outputs[1])[1]
    assert parse_output(outputs[0])[1] is not None
