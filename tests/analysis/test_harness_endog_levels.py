from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from borges.analysis.harness import parse_output
from tests.analysis.test_harness_design import HEADER, run_model

MEDIAN = (
    HEADER
    + """
    x = sm.add_constant(df[["x"]].to_numpy())
    fit = sm.QuantReg(df["y"].to_numpy(), x).fit(q=0.5)
    low, high = fit.conf_int()[1]
    return {"estimate": float(fit.params[1]), "ci_low": float(low), "ci_high": float(high),
            "p_value": float(fit.pvalues[1]), "n": int(fit.nobs)}
"""
)


def test_the_design_reports_how_many_values_the_outcome_takes(tmp_path: Path) -> None:
    rng = np.random.default_rng(3)
    frame = pd.DataFrame({"x": rng.normal(size=300)})
    frame["y"] = np.clip(np.round(0.3 * frame["x"] + rng.normal(size=300)), -1, 1)
    frame.to_parquet(tmp_path / "data.parquet")
    (tmp_path / "state").mkdir()
    frame.to_parquet(tmp_path / "state" / "df.parquet")
    (tmp_path / "state" / "ctx.json").write_text(json.dumps({"covariates": []}))
    done = run_model(tmp_path, MEDIAN)
    assert done.returncode == 0, done.stdout
    traces, _ = parse_output(done.stdout)
    assert traces[0].design is not None
    assert traces[0].design["model"] == "QuantReg" and traces[0].design["endog_levels"] == 3
