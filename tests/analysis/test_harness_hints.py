from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from borges.analysis.harness import parse_error, render_step
from tests.analysis.test_harness_effects import DROPS_AND_REORDERS, make, run

DISTRIBUTION_HINT = (
    "statsmodels has no probability distributions here: read p-values from the fitted result "
    "(result.pvalues) and intervals from result.conf_int(); if you really need a distribution "
    "use scipy.stats.norm"
)
COVARIATE_HINT = (
    "to choose which covariates a later model uses, keep every column and store the list of "
    "names in ctx (for example ctx['covariates'] = [...]); the model step reads that list"
)


def _uses(attribute: str, module: str = "statsmodels.api") -> str:
    return (
        f"import {module} as sm\n\n"
        "def estimate(df, ctx):\n"
        f"    p = sm.{attribute}.cdf(1.0)\n"
        '    return {"estimate": 0.0, "ci_low": -1.0, "ci_high": 1.0, "p_value": p, "n": 1}\n'
    )


@pytest.mark.parametrize("attribute", ["norm", "t", "chi2", "f"])
def test_statsmodels_distribution_attribute_gets_the_hint(tmp_path: Path, attribute: str) -> None:
    done, error, _ = run(tmp_path, *make("model", _uses(attribute)))
    assert done.returncode == 1
    assert error is not None and f"has no attribute '{attribute}'" in error
    assert DISTRIBUTION_HINT in error


def test_statsmodels_submodule_gets_the_hint(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("model", _uses("norm", "statsmodels.formula.api")))
    assert error is not None and DISTRIBUTION_HINT in error


def test_unrelated_attribute_error_gets_no_hint(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("model", _uses("bogus")))
    assert error is not None and "distributions" not in error


def test_dropped_columns_error_explains_covariate_choice(tmp_path: Path) -> None:
    done, error, _ = run(tmp_path, *make("transform", DROPS_AND_REORDERS))
    assert error is not None and COVARIATE_HINT in error


STRING_COVARIATE_MODEL = """
import numpy as np
import statsmodels.api as sm

def estimate(df, ctx):
    X = sm.add_constant(df[ctx["covariates"]].astype(float))
    fit = sm.OLS(df["x"], X).fit()
    return {"estimate": 0.0, "ci_low": -1.0, "ci_high": 1.0, "p_value": 0.5, "n": len(df)}
"""
ENCODING_HINT = "encode them with pd.get_dummies(..., drop_first=True, dtype=float)"


def _run_model(tmp_path: Path, code: str, ctx: dict) -> str | None:
    frame = pd.DataFrame(
        {
            "x": [1.0, 2.0, 3.0, 4.0],
            "job": ["admin.", "tech", "admin.", "tech"],
            "age": [1, 2, 3, 4],
        }
    )
    frame.to_parquet(tmp_path / "data.parquet")
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "ctx.json").write_text(json.dumps(ctx))
    step, option = make("model", code)
    (tmp_path / "step.py").write_text(render_step(step, option, split_half=False))
    done = subprocess.run(
        [sys.executable, "step.py"], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )
    assert done.returncode == 1
    return parse_error(done.stdout)


def test_string_covariate_in_a_model_step_names_the_columns(tmp_path: Path) -> None:
    error = _run_model(tmp_path, STRING_COVARIATE_MODEL, {"covariates": ["age", "job"]})
    assert error is not None and "could not convert string to float: 'admin.'" in error
    assert "non-numeric columns among the model inputs: ['job']" in error
    assert ENCODING_HINT in error


def test_encoding_hint_is_absent_for_other_errors(tmp_path: Path) -> None:
    error = _run_model(tmp_path, _uses("bogus"), {})
    assert error is not None and ENCODING_HINT not in error


def test_a_decimal_put_into_an_integer_column_gets_the_cast_hint(tmp_path: Path) -> None:
    code = "def apply(df, ctx):\n    df.loc[df.index[:5], 'z'] = 0.5\n    return df\n"
    done, error, _ = run(tmp_path, *make("transform", code))
    assert done.returncode == 1 and error is not None
    assert "for dtype 'int64'" in error
    assert "convert the column first, for example df[col] = df[col].astype(float)" in error
