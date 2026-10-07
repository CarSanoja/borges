from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from borges.analysis.harness import parse_error, render_step
from borges.analysis.models import Option, Step

OWN_CLUSTERS = """
import statsmodels.api as sm

def estimate(df, ctx):
    fit = sm.OLS(df["rel"], sm.add_constant(df[["high"]])).fit(
        cov_type="cluster", cov_kwds={"groups": df["day"]}
    )
    low, high = fit.conf_int().loc["high"]
    return {"estimate": float(fit.params["high"]), "ci_low": float(low), "ci_high": float(high),
            "p_value": float(fit.pvalues["high"]), "n": int(len(df))}
"""
ROBUST = OWN_CLUSTERS.replace(
    'cov_type="cluster", cov_kwds={"groups": df["day"]}', 'cov_type="HC3"'
)


def frame(days: int) -> pd.DataFrame:
    rng = np.random.default_rng(3)
    data = pd.DataFrame({"day": np.arange(275) % days, "high": rng.integers(0, 2, 275)})
    data["rel"] = rng.normal(5, 2, len(data))
    return data.astype(float)


def run(
    tmp_path: Path, days: int, code: str, full_data_checks: bool, cluster_by: str | None = None
):
    (tmp_path / "state").mkdir(exist_ok=True)
    frame(days).to_parquet(tmp_path / "state" / "df.parquet")
    (tmp_path / "state" / "ctx.json").write_text(json.dumps({}))
    option = Option(
        id="m", label="OLS", rationale="r", spec="OLS.", code=code, cluster_by=cluster_by
    )
    step = Step(id="s", title="Model", kind="model", description="d", options=[option])
    rendered = render_step(step, option, full_data_checks=full_data_checks)
    (tmp_path / "step.py").write_text(rendered)
    return subprocess.run(
        [sys.executable, "step.py"], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )


def test_errors_clustered_by_the_code_on_thirteen_days_fail_the_universe(tmp_path: Path) -> None:
    done = run(tmp_path, 13, OWN_CLUSTERS, full_data_checks=True)
    assert done.returncode != 0
    assert "clustered on only 13 groups" in (parse_error(done.stdout) or "")


def test_the_harness_clustering_is_checked_too(tmp_path: Path) -> None:
    done = run(tmp_path, 13, ROBUST, full_data_checks=True, cluster_by="day")
    assert done.returncode != 0
    assert "clustered on only 13 groups" in (parse_error(done.stdout) or "")


def test_twenty_or_more_clusters_pass(tmp_path: Path) -> None:
    assert run(tmp_path, 20, OWN_CLUSTERS, full_data_checks=True).returncode == 0
    assert run(tmp_path, 25, ROBUST, full_data_checks=True, cluster_by="day").returncode == 0


def test_the_smoke_run_and_reproduce_skip_the_check(tmp_path: Path) -> None:
    assert run(tmp_path, 13, OWN_CLUSTERS, full_data_checks=False).returncode == 0


def test_robust_errors_without_clusters_pass(tmp_path: Path) -> None:
    assert run(tmp_path, 13, ROBUST, full_data_checks=True).returncode == 0
