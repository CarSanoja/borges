from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from borges.analysis.code_guard import check_code
from borges.analysis.harness import parse_error, parse_output, render_step
from borges.analysis.models import AnalysisResult, Option, Step
from borges.gateway.code_evidence import CodeEvidence, collecting

ROOT = Path(__file__).resolve().parents[2]

LOGIT = """
import numpy as np
import pandas as pd
import statsmodels.api as sm


def estimate(df, ctx):
    x = sm.add_constant(df[["x"]].astype(float))
    fit = sm.Logit(df["y"].astype(float), x).fit(disp=0, cov_type="HC3")
    low, high = fit.conf_int().loc["x"]
    return {"estimate": float(fit.params["x"]), "ci_low": float(low), "ci_high": float(high),
            "p_value": float(fit.pvalues["x"]), "n": int(fit.nobs)}
"""
OLS = LOGIT.replace(
    'sm.Logit(df["y"].astype(float), x).fit(disp=0, cov_type="HC3")',
    'sm.OLS(df["y"].astype(float), x).fit(cov_type="HC1")',
)
GLM = LOGIT.replace(
    'sm.Logit(df["y"].astype(float), x).fit(disp=0, cov_type="HC3")',
    'sm.GLM(df["y"].astype(float), x, family=sm.families.Binomial()).fit()',
)
QUANTILE = LOGIT.replace(
    'sm.Logit(df["y"].astype(float), x).fit(disp=0, cov_type="HC3")',
    'sm.QuantReg(df["y"].astype(float), x).fit(q=0.5)',
)
ARRAYS = (
    LOGIT.replace('df[["x"]].astype(float)', 'df[["x"]].astype(float).to_numpy()')
    .replace('fit.conf_int().loc["x"]', "fit.conf_int()[1]")
    .replace('fit.params["x"]', "fit.params[1]")
    .replace('fit.pvalues["x"]', "fit.pvalues[1]")
    .replace('sm.Logit(df["y"].astype(float), x)', 'sm.Logit(df["y"].to_numpy(dtype=float), x)')
)


@pytest.fixture
def grouped(tmp_path: Path) -> Path:
    rng = np.random.default_rng(11)
    units = rng.integers(0, 60, 1500)
    shift = rng.normal(size=60)[units]
    unit_effect = rng.normal(size=60)[units]
    x = 2 * shift + 0.3 * rng.normal(size=1500)
    frame = pd.DataFrame({"unit": units, "x": x})
    frame["y"] = (rng.random(1500) < 1 / (1 + np.exp(-(0.3 * x + 2 * unit_effect)))).astype(int)
    (tmp_path / "state").mkdir()
    frame.to_parquet(tmp_path / "state" / "df.parquet")
    (tmp_path / "state" / "ctx.json").write_text(json.dumps({}))
    return tmp_path


def run(workdir: Path, code: str, cluster_by: str | None) -> subprocess.CompletedProcess:
    option = Option(
        id="o",
        label="l",
        rationale="r",
        spec="s",
        is_default=True,
        code=code,
        cluster_by=cluster_by,
    )
    step = Step(id="model", title="t", kind="model", description="d", options=[option])
    (workdir / "step.py").write_text(render_step(step, option))
    return subprocess.run(
        [sys.executable, "step.py"], cwd=workdir, capture_output=True, text=True, timeout=300
    )


def result_of(done: subprocess.CompletedProcess) -> AnalysisResult:
    assert done.returncode == 0, done.stdout
    result = parse_output(done.stdout)[1]
    assert result is not None
    return result


@pytest.mark.parametrize("code", [LOGIT, OLS, GLM], ids=["logit", "ols", "glm"])
def test_a_cluster_option_fits_clustered_errors_for_each_family(grouped: Path, code: str) -> None:
    plain = result_of(run(grouped, code, None))
    clustered = result_of(run(grouped, code, "unit"))
    assert clustered.estimate == pytest.approx(plain.estimate, rel=1e-9)
    assert clustered.ci_high - clustered.ci_low > 1.5 * (plain.ci_high - plain.ci_low)
    traces, _ = parse_output(run(grouped, code, "unit").stdout)
    assert traces[0].design is not None and traces[0].design["cov_type"] == "cluster"


def test_the_clustered_interval_is_the_statsmodels_cluster_covariance(grouped: Path) -> None:
    import statsmodels.api as sm

    frame = pd.read_parquet(grouped / "state" / "df.parquet")
    exog = sm.add_constant(frame[["x"]].astype(float))
    fit = sm.Logit(frame["y"].astype(float), exog).fit(
        disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(frame["unit"])[0]}
    )
    low, high = fit.conf_int().loc["x"]
    got = result_of(run(grouped, LOGIT, "unit"))
    assert (got.estimate, got.ci_low, got.ci_high, got.p_value) == pytest.approx(
        (fit.params["x"], low, high, fit.pvalues["x"]), rel=1e-12
    )


def test_a_model_without_a_cluster_covariance_fails_instead_of_reporting_unclustered(
    grouped: Path,
) -> None:
    done = run(grouped, QUANTILE, "unit")
    assert done.returncode == 1
    error = parse_error(done.stdout)
    assert error is not None and "errors clustered by 'unit'" in error


def test_rows_that_cannot_be_matched_to_the_data_fail_with_a_reason(grouped: Path) -> None:
    done = run(
        grouped,
        ARRAYS.replace("df[[", "df[df['x'] > 0][[").replace(
            'df["y"].to_numpy', 'df[df["x"] > 0]["y"].to_numpy'
        ),
        "unit",
    )
    assert done.returncode == 1
    error = parse_error(done.stdout)
    assert error is not None and "cannot cluster the errors by 'unit'" in error


def test_a_missing_cluster_column_fails_with_a_reason(grouped: Path) -> None:
    done = run(grouped, LOGIT, "ghost")
    error = parse_error(done.stdout)
    assert done.returncode == 1 and error is not None and "no such column" in error


def test_the_gateway_accepts_the_step_of_a_guarded_option_that_clusters(tmp_path: Path) -> None:
    evidence = CodeEvidence()
    with collecting(evidence):
        assert check_code(LOGIT, "model", "") == []
    option = Option(id="o", label="l", rationale="r", spec="s", code=LOGIT, cluster_by="unit")
    step = Step(id="model", title="t", kind="model", description="d", options=[option])
    assert evidence.covers(render_step(step, option))


CASE = ROOT / "cases" / "red_cards" / "data.parquet"
BASELINE = """
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm


def estimate(df, ctx):
    data = df[df["rater1"].notna() & df["rater2"].notna()].copy()
    data["red_flag"] = (data["redCards"] >= 1).astype(int)
    score = (data["rater1"] + data["rater2"]) / 2
    data["skin_group"] = (score >= score.median()).astype(int)
    columns = ["skin_group", "games", "leagueCountry"]
    dummies = pd.get_dummies(data[columns], columns=["leagueCountry"], drop_first=True)
    exog = sm.add_constant(dummies.astype(float))
    fit = sm.Logit(data["red_flag"], exog).fit(disp=0, cov_type="HC3")
    b, se = fit.params["skin_group"], fit.bse["skin_group"]
    z = 1.959963984540054
    return {"estimate": float(np.exp(b)), "ci_low": float(np.exp(b - z * se)),
            "ci_high": float(np.exp(b + z * se)), "p_value": float(2 * norm.cdf(-abs(b / se))),
            "n": int(len(data))}
"""


def test_the_clustered_option_on_the_red_cards_baseline_reproduces_the_refit(
    tmp_path: Path,
) -> None:
    (tmp_path / "state").mkdir()
    pd.read_parquet(CASE).to_parquet(tmp_path / "state" / "df.parquet")
    (tmp_path / "state" / "ctx.json").write_text(json.dumps({}))
    hc3 = result_of(run(tmp_path, BASELINE, None))
    assert (hc3.estimate, hc3.ci_low, hc3.ci_high) == pytest.approx(
        (1.1702, 1.0497, 1.3047), abs=5e-5
    )
    assert hc3.n == 124621
    clustered = result_of(run(tmp_path, BASELINE, "playerShort"))
    assert clustered.n == 124621
    assert clustered.estimate == pytest.approx(1.1702, abs=5e-5)
    assert clustered.ci_low == pytest.approx(1.0169, abs=5e-5)
    assert clustered.ci_high == pytest.approx(1.3468, abs=5e-5)
    assert clustered.p_value == pytest.approx(0.0283, abs=5e-5)
