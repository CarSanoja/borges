from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from borges.analysis.code_guard import check_code
from borges.analysis.model_spec.render import render_code
from tests.analysis.model_spec.data import make_spec, synthetic


def weighted_frame() -> pd.DataFrame:
    frame = synthetic()
    rng = np.random.default_rng(11)
    weights = rng.integers(1, 40, len(frame)).astype(float)
    weights[:5] = [0.0, -2.0, np.nan, np.inf, 3.0]
    return frame.assign(w=weights)


def run(spec: object, data: pd.DataFrame) -> dict:
    code = render_code(spec)
    namespace: dict = {}
    exec(code, namespace)
    return namespace["estimate"](data, {})


def kept(data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows = data.dropna(subset=columns)
    rows = rows[np.isfinite(rows[columns].astype(float)).all(axis=1)]
    return rows[rows["w"] > 0]


def design(rows: pd.DataFrame) -> pd.DataFrame:
    return sm.add_constant(rows[["x", "a"]].astype(float))


@pytest.mark.parametrize("cov", ["HC3", "nonrobust"])
def test_wls_equals_statsmodels(cov: str) -> None:
    data = weighted_frame()
    spec = make_spec("ols", covariates=["a"], weights="w", cov_type=cov)
    got = run(spec, data)
    rows = kept(data, ["y_cont", "x", "a", "w"])
    fit = sm.WLS(rows["y_cont"], design(rows), weights=rows["w"]).fit(cov_type=cov)
    low, high = fit.conf_int().loc["x"]
    assert got["estimate"] == pytest.approx(fit.params["x"], abs=1e-6)
    assert got["ci_low"] == pytest.approx(low, abs=1e-6)
    assert got["ci_high"] == pytest.approx(high, abs=1e-6)
    assert got["p_value"] == pytest.approx(fit.pvalues["x"], abs=1e-6)
    assert got["n"] == len(rows)


def test_wls_with_cluster_equals_statsmodels() -> None:
    data = weighted_frame()
    spec = make_spec("ols", covariates=["a"], weights="w", cov_type="cluster", cluster="g")
    got = run(spec, data)
    rows = kept(data, ["y_cont", "x", "a", "w", "g"])
    groups = pd.factorize(rows["g"])[0]
    fit = sm.WLS(rows["y_cont"], design(rows), weights=rows["w"]).fit(
        cov_type="cluster", cov_kwds={"groups": groups}
    )
    assert got["estimate"] == pytest.approx(fit.params["x"], abs=1e-6)
    assert got["p_value"] == pytest.approx(fit.pvalues["x"], abs=1e-6)
    assert got["ci_low"] == pytest.approx(fit.conf_int().loc["x"][0], abs=1e-6)


def test_weighted_binary_outcome_uses_variance_weights() -> None:
    data = weighted_frame()
    spec = make_spec("logit", covariates=["a"], weights="w", cov_type="HC1", report="odds_ratio")
    got = run(spec, data)
    rows = kept(data, ["y_bin", "x", "a", "w"])
    model = sm.GLM(
        rows["y_bin"], design(rows), family=sm.families.Binomial(), var_weights=rows["w"]
    )
    fit = model.fit(cov_type="HC1")
    assert got["extra"]["coefficient"] == pytest.approx(fit.params["x"], abs=1e-6)
    assert got["estimate"] == pytest.approx(np.exp(fit.params["x"]), abs=1e-6)
    assert got["p_value"] == pytest.approx(fit.pvalues["x"], abs=1e-6)


def test_weighted_poisson_uses_variance_weights() -> None:
    data = weighted_frame()
    spec = make_spec("poisson", covariates=["a"], weights="w", cov_type="HC0")
    got = run(spec, data)
    rows = kept(data, ["y_count", "x", "a", "w"])
    model = sm.GLM(
        rows["y_count"], design(rows), family=sm.families.Poisson(), var_weights=rows["w"]
    )
    fit = model.fit(cov_type="HC0")
    assert got["estimate"] == pytest.approx(fit.params["x"], abs=1e-6)


def test_weighted_negbin_runs() -> None:
    data = weighted_frame()
    got = run(make_spec("negbin", covariates=["a"], weights="w"), data)
    assert np.isfinite(got["estimate"])


@pytest.mark.parametrize(
    ("family", "intent"),
    [
        ("ols", "WLS (weights = students) with cluster-robust SEs (prof)"),
        ("logit", "Weighted logistic regression by w"),
        ("poisson", "Poisson regression weighted by w"),
    ],
)
def test_rendered_weighted_code_passes_the_guard(family: str, intent: str) -> None:
    extra = {"cov_type": "cluster", "cluster": "g"} if family == "ols" else {}
    code = render_code(make_spec(family, weights="w", **extra))
    assert check_code(code, "model", intent) == []
