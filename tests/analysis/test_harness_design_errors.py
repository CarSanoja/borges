from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from borges.analysis.harness import parse_error
from tests.analysis.test_harness_design import HEADER, run_model

ONE_DUMMY_PER_ROW = (
    HEADER
    + """
    x = pd.get_dummies(df["respondent"], prefix="r", dtype=float)
    x["x"] = df["x"]
    fit = sm.OLS(df["y"], x).fit()
    low, high = fit.conf_int().loc["x"]
    return {"estimate": float(fit.params["x"]), "ci_low": float(low), "ci_high": float(high),
            "p_value": float(fit.pvalues["x"]), "n": int(fit.nobs)}
"""
)


def test_a_design_wider_than_its_rows_fails_with_the_reason_not_a_crash(tmp_path: Path) -> None:
    rng = np.random.default_rng(3)
    frame = pd.DataFrame({"respondent": [f"w{i}" for i in range(12)], "x": rng.normal(size=12)})
    frame["y"] = frame["x"] + rng.normal(size=12)
    frame.to_parquet(tmp_path / "data.parquet")
    done = run_model(tmp_path, ONE_DUMMY_PER_ROW)
    assert done.returncode == 1
    error = parse_error(done.stdout)
    assert error is not None
    assert "zero-size array" not in error
    assert "13 columns but only 12 rows reach the model" in error
    assert "must not be dummy-coded" in error


OUTCOME_IN_THE_LIST = (
    HEADER
    + """
    d = df.copy()
    d["inter"] = d["a"] * d["b"]
    use = ["y", "a", "b", "inter"]
    fit = sm.OLS(d["y"], sm.add_constant(d[use])).fit(cov_type="HC3")
    low, high = fit.conf_int().loc["inter"]
    return {"estimate": float(fit.params["inter"]), "ci_low": float(low), "ci_high": float(high),
            "p_value": float(fit.pvalues["inter"]), "n": int(fit.nobs)}
"""
)


def test_a_regressor_that_is_the_outcome_is_named_not_reported_as_a_degenerate_interval(
    tmp_path: Path,
) -> None:
    rng = np.random.default_rng(5)
    frame = pd.DataFrame({"a": rng.integers(0, 2, 200), "b": rng.integers(0, 2, 200)})
    frame["y"] = 1.0 + 0.5 * frame["a"] * frame["b"] + rng.normal(size=200)
    frame.to_parquet(tmp_path / "data.parquet")
    done = run_model(tmp_path, OUTCOME_IN_THE_LIST)
    assert done.returncode == 1
    error = parse_error(done.stdout)
    assert error is not None
    assert "degenerate" not in error
    assert "outcome is also one of its regressors: ['y']" in error


def test_a_regressor_close_to_the_outcome_is_not_refused(tmp_path: Path) -> None:
    rng = np.random.default_rng(6)
    frame = pd.DataFrame({"a": rng.integers(0, 2, 200), "b": rng.integers(0, 2, 200)})
    frame["y"] = 1.0 + 0.5 * frame["a"] * frame["b"] + rng.normal(size=200)
    frame["y_lag"] = frame["y"] + rng.normal(scale=0.01, size=200)
    frame.to_parquet(tmp_path / "data.parquet")
    done = run_model(tmp_path, OUTCOME_IN_THE_LIST.replace('["y", "a"', '["y_lag", "a"'))
    assert done.returncode == 0, done.stdout
