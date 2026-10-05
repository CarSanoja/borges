from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from borges.analysis.harness import parse_output
from tests.analysis.test_harness_design import HEADER, run_model

RESULT = """
    low, high = fit.conf_int().loc["x"]
    return {"estimate": float(fit.params["x"]), "ci_low": float(low), "ci_high": float(high),
            "p_value": float(fit.pvalues["x"]), "n": int(fit.nobs)}
"""
LOG1P = (
    HEADER
    + """
    fit = sm.OLS(np.log1p(df["deaths"]), sm.add_constant(df[["x"]])).fit()
"""
    + RESULT
)
LOG_COLUMN = (
    HEADER
    + """
    fit = sm.OLS(df["log_deaths"], sm.add_constant(df[["x"]])).fit()
"""
    + RESULT
)
RAW = (
    HEADER
    + """
    fit = sm.OLS(df["deaths"], sm.add_constant(df[["x"]])).fit()
"""
    + RESULT
)
POISSON = (
    HEADER
    + """
    fit = sm.GLM(df["deaths"], sm.add_constant(df[["x"]]), family=sm.families.Poisson()).fit()
"""
    + RESULT
)

GAMMA_LOWER_CASE_LOG = (
    HEADER
    + """
    family = sm.families.Gamma(link=sm.families.links.log())
    fit = sm.GLM(df["deaths"] + 1.0, sm.add_constant(df[["x"]]), family=family).fit()
"""
    + RESULT
)


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    rng = np.random.default_rng(2)
    x = rng.normal(size=150)
    frame = pd.DataFrame({"x": x, "deaths": rng.poisson(np.exp(1.0 + 0.3 * x)).astype(float)})
    frame["log_deaths"] = np.log1p(frame["deaths"])
    frame.to_parquet(tmp_path / "data.parquet")
    return tmp_path


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (LOG1P, {"kind": "log1p", "column": "deaths"}),
        (LOG_COLUMN, {"kind": "log1p", "column": "deaths"}),
        (POISSON, {"kind": "log link", "column": "deaths"}),
        (GAMMA_LOWER_CASE_LOG, {"kind": "log link", "column": "deaths"}),
        (RAW, None),
    ],
)
def test_the_scale_of_the_reported_estimate_is_recorded(
    workdir: Path, code: str, expected: dict[str, str] | None
) -> None:
    done = run_model(workdir, code)
    assert done.returncode == 0, done.stdout
    traces, _ = parse_output(done.stdout)
    assert traces[0].design is not None
    assert traces[0].design.get("outcome_log") == expected
