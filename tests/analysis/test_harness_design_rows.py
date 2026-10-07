from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from borges.analysis.harness import parse_output, render_step
from borges.analysis.models import Option, Step

OLS = """
import statsmodels.formula.api as smf


def estimate(df, ctx):
    data = df.dropna(subset=["y", "x"])__REORDER__
    fit = smf.ols("y ~ x", data=data).fit()
    lo, hi = fit.conf_int().loc["x"]
    return {"estimate": float(fit.params["x"]), "ci_low": float(lo), "ci_high": float(hi),
            "p_value": float(fit.pvalues["x"]), "n": int(fit.nobs)}
"""
FRAME = pd.DataFrame(
    {
        "pid": ["a", "b", "c", "d", "e", "f"],
        "y": [1.0, 2.0, 2.5, 4.0, None, 5.0],
        "x": [0.0, 1.0, 1.0, 0.0, 1.0, 1.0],
    }
)


def fitted(tmp_path: Path, reorder: str = "") -> dict[str, object]:
    option = Option(
        id="o", label="o", rationale="r", spec="s", code=OLS.replace("__REORDER__", reorder)
    )
    step = Step(id="m", title="m", kind="model", description="d", options=[option])
    (tmp_path / "state").mkdir()
    FRAME.to_parquet(tmp_path / "state" / "df.parquet")
    (tmp_path / "state" / "ctx.json").write_text(json.dumps({}))
    (tmp_path / "step.py").write_text(render_step(step, option, row_key="pid"))
    done = subprocess.run(
        [sys.executable, "step.py"], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )
    traces, result = parse_output(done.stdout)
    assert result is not None, done.stdout
    return traces[-1].design or {}


def test_the_model_trace_names_the_fitted_rows_by_their_key_and_each_column_mean(
    tmp_path: Path,
) -> None:
    """The repair of a starting point needs the rows an independent implementation fits that
    the step-by-step code does not, and how each column is coded."""
    design = fitted(tmp_path)
    assert design["row_keys"] == ["a", "b", "c", "d", "f"]
    assert design["means"] == {"Intercept": 1.0, "x": 0.6}
    assert "rows" not in design and "endog_check" not in design


def test_rows_the_code_reordered_are_not_named(tmp_path: Path) -> None:
    design = fitted(tmp_path, ".iloc[::-1].reset_index(drop=True)")
    assert "row_keys" not in design
