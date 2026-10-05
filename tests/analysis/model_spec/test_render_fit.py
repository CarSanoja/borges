from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from borges.analysis.model_spec.render import render_code
from borges.analysis.model_spec.validate import validate_spec
from tests.analysis.model_spec.data import make_spec, synthetic


def experiment(rows: int = 600, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    variant = rng.choice(["treatment", "control"], rows)
    age = rng.normal(size=rows)
    logit = -0.4 + 0.5 * (variant == "treatment") + 0.3 * age
    return pd.DataFrame(
        {
            "variant": variant,
            "age": age,
            "region": rng.integers(0, 25, rows),
            "converted": (rng.random(rows) < 1 / (1 + np.exp(-logit))).astype(float),
        }
    )


def marginal_spec() -> object:
    return make_spec(
        "logit",
        outcome="converted",
        exposure="variant",
        exposure_level="treatment",
        covariates=["age"],
        cov_type="cluster",
        cluster="region",
        report="marginal_effect",
    )


def test_marginal_effect_is_the_difference_of_mean_predicted_probabilities() -> None:
    data = experiment()
    namespace: dict = {}
    exec(render_code(marginal_spec()), namespace)
    got = namespace["estimate"](data, {})
    coded = data.assign(variant=(data.variant == "treatment").astype(float))
    exog = sm.add_constant(coded[["variant", "age"]])
    fit = sm.Logit(coded["converted"], exog).fit(disp=0)
    on, off = exog.copy(), exog.copy()
    on["variant"], off["variant"] = 1.0, 0.0
    expected = float(np.mean(fit.predict(on)) - np.mean(fit.predict(off)))
    assert got["estimate"] == pytest.approx(expected, abs=1e-6)
    assert abs(got["estimate"]) < 1.0
    assert got["ci_low"] < got["estimate"] < got["ci_high"]
    assert 0.0 <= got["p_value"] <= 1.0
    assert got["n"] == len(data) and got["extra"]["std_err"] > 0


def test_odds_ratio_and_coefficient_reports_are_unchanged_for_a_text_exposure() -> None:
    data = experiment()
    spec = make_spec("logit", outcome="converted", exposure="variant", exposure_level="treatment")
    namespace: dict = {}
    exec(render_code(spec), namespace)
    coefficient = namespace["estimate"](data, {})["estimate"]
    ratio_spec = spec.model_copy(update={"report": "odds_ratio"})
    namespace = {}
    exec(render_code(ratio_spec), namespace)
    assert namespace["estimate"](data, {})["estimate"] == pytest.approx(np.exp(coefficient))


def test_quasi_poisson_keeps_the_poisson_estimate_and_scales_its_errors() -> None:
    frame = synthetic().dropna()
    namespace: dict = {}
    exec(render_code(make_spec("quasipoisson", report="coefficient")), namespace)
    got = namespace["estimate"](frame, {})
    exog = sm.add_constant(frame[["x"]].astype(float), has_constant="add")
    poisson = sm.GLM(frame["y_count"], exog, family=sm.families.Poisson()).fit()
    dispersion = float(poisson.pearson_chi2 / poisson.df_resid)
    assert got["estimate"] == pytest.approx(float(poisson.params["x"]), rel=1e-9)
    half = (got["ci_high"] - got["ci_low"]) / 2
    expected = 1.959963984540054 * float(poisson.bse["x"]) * np.sqrt(dispersion)
    assert half == pytest.approx(expected, rel=1e-6)


def test_a_z_scored_outcome_and_the_fitted_dispersion_are_noted() -> None:
    frame = synthetic().dropna()
    namespace: dict = {}
    exec(render_code(make_spec("ols", outcome="y_cont", standardize=["y_cont", "x"])), namespace)
    assert (
        "outcome z-scored with the predictors: y_cont" in namespace["estimate"](frame, {})["note"]
    )
    exec(render_code(make_spec("negbin")), namespace)
    assert "negative binomial alpha" in namespace["estimate"](frame, {})["note"]


def test_quasi_poisson_with_a_sandwich_covariance_is_refused() -> None:
    spec = make_spec("quasipoisson", report="rate_ratio", cov_type="HC0")
    assert any("ignores that scale" in p for p in validate_spec(spec, ["y_count", "x"]))
    assert not validate_spec(make_spec("quasipoisson", report="rate_ratio"), ["y_count", "x"])
