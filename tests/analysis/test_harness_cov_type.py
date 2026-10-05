from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from borges.analysis.harness import parse_output
from tests.analysis.test_harness_design import HEADER, run_model

LOGIT_HC3 = (
    HEADER
    + """
    x = sm.add_constant(df[["x"]].to_numpy())
    fit = sm.Logit(df["y"].to_numpy(), x).fit(disp=0, cov_type="HC3")
    low, high = fit.conf_int()[1]
    return {"estimate": float(fit.params[1]), "ci_low": float(low), "ci_high": float(high),
            "p_value": float(fit.pvalues[1]), "n": int(fit.nobs)}
"""
)


def test_the_design_reports_the_covariance_the_fit_asked_for(tmp_path: Path) -> None:
    rng = np.random.default_rng(5)
    frame = pd.DataFrame({"x": rng.normal(size=400)})
    frame["y"] = (rng.random(400) < 1 / (1 + np.exp(-0.5 * frame["x"]))).astype(int)
    frame.to_parquet(tmp_path / "data.parquet")
    (tmp_path / "state").mkdir()
    frame.to_parquet(tmp_path / "state" / "df.parquet")
    (tmp_path / "state" / "ctx.json").write_text(json.dumps({"covariates": []}))
    done = run_model(tmp_path, LOGIT_HC3)
    assert done.returncode == 0, done.stdout
    traces, _ = parse_output(done.stdout)
    assert traces[0].design is not None
    assert traces[0].design["model"] == "Logit" and traces[0].design["cov_type"] == "HC3"
