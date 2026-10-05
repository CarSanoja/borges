from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from borges.analysis.harness import parse_error, parse_output
from borges.analysis.model_spec.render_design import ALIAS_NOTE
from tests.analysis.test_harness_design import HEADER, run_model

FIT = (
    HEADER
    + """
    x = sm.add_constant(df[ctx["covariates"] + ["x"]], has_constant="add")
    fit = sm.OLS(df["y"], x).fit(cov_type="HC3")
    low, high = fit.conf_int().loc["x"]
    return {"estimate": float(fit.params["x"]), "ci_low": float(low), "ci_high": float(high),
            "p_value": float(fit.pvalues["x"]), "n": int(fit.nobs)}
"""
)


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    rng = np.random.default_rng(1)
    year = rng.integers(1950, 2013, size=150).astype(float)
    frame = pd.DataFrame({"year": year, "elapsed": 2014.0 - year, "x": rng.normal(size=150)})
    frame["double_x"] = 2.0 * frame["x"]
    frame["internal"] = 0.0
    frame["y"] = 0.4 * frame["x"] + 0.01 * frame["year"] + rng.normal(size=150)
    frame.to_parquet(tmp_path / "data.parquet")
    return tmp_path


def with_ctx(workdir: Path, covariates: list[str]) -> None:
    (workdir / "state").mkdir(exist_ok=True)
    pd.read_parquet(workdir / "data.parquet").to_parquet(workdir / "state" / "df.parquet")
    (workdir / "state" / "ctx.json").write_text(json.dumps({"covariates": covariates}))


def test_aliasing_among_ctx_covariates_passes_with_the_lm_estimate(workdir: Path) -> None:
    with_ctx(workdir, ["year", "elapsed"])
    done = run_model(workdir, FIT)
    assert done.returncode == 0, done.stdout
    traces, result = parse_output(done.stdout)
    assert traces[0].note == ALIAS_NOTE + "elapsed"
    frame = pd.read_parquet(workdir / "data.parquet")
    reference = sm.OLS(frame["y"], sm.add_constant(frame[["year", "x"]])).fit(cov_type="HC3")
    assert result is not None
    assert result.estimate == pytest.approx(float(reference.params["x"]), rel=1e-8)
    assert result.ci_low == pytest.approx(float(reference.conf_int().loc["x", 0]), rel=1e-6)


def test_aliasing_that_involves_the_exposure_still_fails(workdir: Path) -> None:
    with_ctx(workdir, ["double_x"])
    done = run_model(workdir, FIT)
    assert done.returncode == 1
    assert "rank-deficient or collinear" in (parse_error(done.stdout) or "")


def test_an_all_zero_ctx_covariate_is_dropped_like_lm_does(workdir: Path) -> None:
    with_ctx(workdir, ["year", "internal"])
    done = run_model(workdir, FIT)
    assert done.returncode == 0, done.stdout
    traces, result = parse_output(done.stdout)
    assert traces[0].note == ALIAS_NOTE + "internal"
    frame = pd.read_parquet(workdir / "data.parquet")
    reference = sm.OLS(frame["y"], sm.add_constant(frame[["year", "x"]])).fit(cov_type="HC3")
    assert result is not None
    assert result.estimate == pytest.approx(float(reference.params["x"]), rel=1e-8)


def test_a_dummy_trap_beside_the_exposure_is_dropped_like_lm(tmp_path: Path) -> None:
    from tests.analysis.test_harness_design import COLLINEAR

    rng = np.random.default_rng(0)
    frame = pd.DataFrame({"x": rng.normal(size=120), "month": ["jan", "feb", "mar", "apr"] * 30})
    frame["y"] = 0.5 * frame["x"] + rng.normal(size=120)
    frame.to_parquet(tmp_path / "data.parquet")
    done = run_model(tmp_path, COLLINEAR)
    assert done.returncode == 0, done.stdout
    traces, result = parse_output(done.stdout)
    assert traces[0].note.startswith(ALIAS_NOTE)
    dummies = pd.get_dummies(frame["month"], prefix="month", dtype=float, drop_first=True)
    reference = sm.OLS(frame["y"], sm.add_constant(pd.concat([frame[["x"]], dummies], axis=1)))
    fit = reference.fit()
    assert result is not None
    assert result.estimate == pytest.approx(float(fit.params["x"]), rel=1e-8)
    assert result.ci_low == pytest.approx(float(fit.conf_int().loc["x", 0]), rel=1e-6)


GROUP_LEVEL = (
    HEADER
    + """
    d = pd.get_dummies(df["group"], prefix="g", drop_first=True, dtype=float)
    x = sm.add_constant(pd.concat([df[["x", "level"]], d], axis=1), has_constant="add")
    fit = sm.OLS(df["y"], x).fit(cov_type="cluster", cov_kwds={"groups": df["group"]})
    low, high = fit.conf_int().loc["x"]
    return {"estimate": float(fit.params["x"]), "ci_low": float(low), "ci_high": float(high),
            "p_value": float(fit.pvalues["x"]), "n": int(fit.nobs)}
"""
)


def test_a_group_level_covariate_beside_group_fixed_effects_is_dropped(tmp_path: Path) -> None:
    rng = np.random.default_rng(3)
    group = np.repeat(np.arange(8), 40)
    frame = pd.DataFrame({"group": group.astype(str), "x": rng.normal(size=group.size)})
    frame["level"] = rng.normal(size=8)[group]
    frame["y"] = 0.3 * frame["x"] + frame["level"] + rng.normal(size=group.size)
    frame.to_parquet(tmp_path / "data.parquet")
    done = run_model(tmp_path, GROUP_LEVEL)
    assert done.returncode == 0, done.stdout
    traces, result = parse_output(done.stdout)
    assert traces[0].note.startswith(ALIAS_NOTE)
    dummies = pd.get_dummies(frame["group"], prefix="g", drop_first=True, dtype=float)
    reference = sm.OLS(frame["y"], sm.add_constant(pd.concat([frame[["x"]], dummies], axis=1)))
    fit = reference.fit(cov_type="cluster", cov_kwds={"groups": frame["group"]})
    assert result is not None
    assert result.estimate == pytest.approx(float(fit.params["x"]), rel=1e-8)
    assert result.ci_low == pytest.approx(float(fit.conf_int().loc["x", 0]), rel=2e-3)


GLM_FIT = (
    HEADER
    + """
    x = sm.add_constant(df[ctx["covariates"] + ["x"]], has_constant="add")
    fit = sm.GLM(df["y"], x, family=sm.families.Gaussian()).fit(cov_type="HC0")
    low, high = fit.conf_int().loc["x"]
    return {"estimate": float(fit.params["x"]), "ci_low": float(low), "ci_high": float(high),
            "p_value": float(fit.pvalues["x"]), "n": int(fit.nobs)}
"""
)


def test_a_glm_names_its_aliased_column_once(workdir: Path) -> None:
    with_ctx(workdir, ["year", "elapsed"])
    done = run_model(workdir, GLM_FIT)
    assert done.returncode == 0, done.stdout
    traces, _ = parse_output(done.stdout)
    assert traces[0].note == ALIAS_NOTE + "elapsed"
