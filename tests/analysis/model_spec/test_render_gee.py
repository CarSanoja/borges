from __future__ import annotations

import numpy as np
import pytest
import statsmodels.api as sm

from borges.analysis.model_spec.render import render_code
from borges.analysis.model_spec.validate import validate_spec
from tests.analysis.model_spec.data import make_spec
from tests.analysis.model_spec.test_render_fit import experiment

COLUMNS = ["converted", "variant", "age", "region"]


def gee_spec(**fields: object) -> object:
    base = {
        "outcome": "converted",
        "exposure": "variant",
        "exposure_level": "treatment",
        "covariates": ["age"],
        "cov_type": "gee",
        "cluster": "region",
    }
    return make_spec("logit", **{**base, **fields})


def test_gee_matches_a_direct_exchangeable_fit() -> None:
    data = experiment()
    namespace: dict = {}
    exec(render_code(gee_spec()), namespace)
    got = namespace["estimate"](data, {})
    coded = data.assign(variant=(data.variant == "treatment").astype(float))
    exog = sm.add_constant(coded[["variant", "age"]])
    fit = sm.GEE(
        coded["converted"],
        exog,
        groups=coded["region"],
        family=sm.families.Binomial(),
        cov_struct=sm.cov_struct.Exchangeable(),
    ).fit()
    assert got["estimate"] == pytest.approx(float(fit.params["variant"]), rel=1e-6)
    low, high = fit.conf_int().loc["variant"]
    assert got["ci_low"] == pytest.approx(float(low), rel=1e-6)
    assert got["ci_high"] == pytest.approx(float(high), rel=1e-6)


def test_gee_reports_an_odds_ratio() -> None:
    data = experiment()
    namespace: dict = {}
    exec(render_code(gee_spec()), namespace)
    coefficient = namespace["estimate"](data, {})["estimate"]
    namespace = {}
    exec(render_code(gee_spec(report="odds_ratio")), namespace)
    assert namespace["estimate"](data, {})["estimate"] == pytest.approx(np.exp(coefficient))


@pytest.mark.parametrize(
    ("fields", "problem"),
    [
        ({"cluster": None}, "cov_type gee needs a cluster column"),
        ({"report": "marginal_effect"}, "GEE reports a coefficient or a ratio"),
    ],
)
def test_gee_specs_the_template_cannot_honour_are_refused(fields: dict, problem: str) -> None:
    assert any(problem in p for p in validate_spec(gee_spec(**fields), COLUMNS))


def test_gee_is_refused_for_negative_binomial() -> None:
    spec = make_spec("negbin", cov_type="gee", cluster="g")
    assert any("GEE is available" in p for p in validate_spec(spec, ["y_count", "x", "g"]))
