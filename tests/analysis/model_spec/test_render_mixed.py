from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from borges.analysis.code_guard import check_code
from borges.analysis.model_spec.render import render_code
from tests.analysis.model_spec.data import make_spec, synthetic

INTENT = "Linear mixed model (random intercept for prof)"


def frame() -> pd.DataFrame:
    data = synthetic()
    rng = np.random.default_rng(5)
    status = np.where(rng.random(len(data)) < 0.4, "committed", "single")
    group = data["g"].astype(float)
    group[[3, 9]] = np.nan
    return data.assign(status=status, g=group)


def run(spec: object, data: pd.DataFrame) -> dict:
    namespace: dict = {}
    exec(render_code(spec), namespace)
    return namespace["estimate"](data, {})


def test_mixed_model_equals_statsmodels() -> None:
    data = frame()
    got = run(make_spec("ols", covariates=["a"], random_intercept="g"), data)
    rows = data.dropna(subset=["y_cont", "x", "a", "g"])
    exog = sm.add_constant(rows[["x", "a"]].astype(float))
    fit = sm.MixedLM(rows["y_cont"], exog, groups=pd.factorize(rows["g"])[0]).fit()
    low, high = fit.conf_int().loc["x"]
    assert got["estimate"] == pytest.approx(fit.params["x"], abs=1e-6)
    assert got["ci_low"] == pytest.approx(low, abs=1e-6)
    assert got["ci_high"] == pytest.approx(high, abs=1e-6)
    assert got["p_value"] == pytest.approx(fit.pvalues["x"], abs=1e-6)
    assert got["n"] == len(rows)


def test_mixed_model_with_a_text_moderator_reports_the_interaction() -> None:
    data = frame()
    spec = make_spec(
        "ols",
        moderator="status",
        moderator_level="committed",
        covariates=["a"],
        random_intercept="g",
    )
    got = run(spec, data)
    rows = data.dropna(subset=["y_cont", "x", "a", "g"])
    flag = (rows["status"] == "committed").astype(float)
    core = pd.DataFrame({"x": rows["x"], "status": flag, "exposure_by_moderator": rows["x"] * flag})
    exog = sm.add_constant(pd.concat([core, rows[["a"]]], axis=1))
    fit = sm.MixedLM(rows["y_cont"], exog, groups=pd.factorize(rows["g"])[0]).fit()
    assert got["estimate"] == pytest.approx(fit.params["exposure_by_moderator"], abs=1e-6)
    assert got["p_value"] == pytest.approx(fit.pvalues["exposure_by_moderator"], abs=1e-6)


def test_mixed_model_with_a_numeric_moderator() -> None:
    data = frame()
    got = run(make_spec("ols", moderator="m", random_intercept="g"), data)
    rows = data.dropna(subset=["y_cont", "x", "m", "g"])
    core = pd.DataFrame(
        {"x": rows["x"], "m": rows["m"], "exposure_by_moderator": rows["x"] * rows["m"]}
    )
    groups = pd.factorize(rows["g"])[0]
    fit = sm.MixedLM(rows["y_cont"], sm.add_constant(core), groups=groups).fit()
    assert got["estimate"] == pytest.approx(fit.params["exposure_by_moderator"], abs=1e-6)


def test_fewer_than_two_groups_raises_with_the_reason() -> None:
    data = frame().assign(g=1.0)
    with pytest.raises(ValueError, match="at least 2 groups in the column g.*fall in 1"):
        run(make_spec("ols", random_intercept="g"), data)


def test_rendered_mixed_code_passes_the_guard() -> None:
    assert check_code(render_code(make_spec("ols", random_intercept="g")), "model", INTENT) == []
