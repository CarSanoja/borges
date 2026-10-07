from __future__ import annotations

import pandas as pd
import pytest
import statsmodels.api as sm

from borges.analysis.model_spec.core_terms import is_core_term
from borges.analysis.model_spec.render import render_code
from tests.analysis.model_spec.data import make_spec, synthetic

CORE = ["y_cont", "x", "m"]


@pytest.mark.parametrize("name", ["x", "x:m", "x*m", "C(x)", "x + m", "m:x"])
def test_terms_made_only_of_core_columns_are_core(name: str) -> None:
    assert is_core_term(name, CORE)


@pytest.mark.parametrize("name", ["x_squared", "a", "x:a", "log(x)", "xm", "C(a)"])
def test_other_terms_are_kept(name: str) -> None:
    assert not is_core_term(name, CORE)


def run(code: str, data: pd.DataFrame, ctx: dict) -> dict:
    namespace: dict = {}
    exec(code, namespace)
    return namespace["estimate"](data, ctx)


def test_core_terms_in_ctx_covariates_are_dropped_and_the_fit_matches() -> None:
    data = synthetic()
    spec = make_spec("ols", moderator="m", covariates_from_ctx=True)
    got = run(render_code(spec), data, {"covariates": ["x", "m", "x:m", "a"]})
    clean = run(render_code(spec), data, {"covariates": ["a"]})
    assert got["estimate"] == pytest.approx(clean["estimate"])
    frame = data.dropna(subset=["y_cont", "x", "m", "a"])
    exog = frame[["x", "m"]].assign(x_m=frame["x"] * frame["m"]).join(frame[["a"]])
    direct = sm.OLS(frame["y_cont"], sm.add_constant(exog)).fit()
    assert got["estimate"] == pytest.approx(float(direct.params["x_m"]), abs=1e-6)


def test_the_fertility_case_renders_code_that_runs() -> None:
    data = synthetic().rename(columns={"x": "fertility_phase", "m": "relationship_status"})
    spec = make_spec(
        "ols", exposure="fertility_phase", moderator="relationship_status", covariates_from_ctx=True
    )
    covariates = ["fertility_phase", "relationship_status", "fertility_phase:relationship_status"]
    got = run(render_code(spec), data, {"covariates": covariates})
    plain = run(render_code(spec), data, {"covariates": []})
    assert got["estimate"] == pytest.approx(plain["estimate"])


def test_a_longer_identifier_containing_a_core_name_is_kept() -> None:
    data = synthetic().assign(x_squared=lambda d: d["x"] ** 2 + d["a"].fillna(0))
    spec = make_spec("ols", covariates_from_ctx=True)
    kept = run(render_code(spec), data, {"covariates": ["x_squared"]})
    without = run(render_code(spec), data, {"covariates": []})
    assert kept["estimate"] != pytest.approx(without["estimate"])
    static = render_code(make_spec("ols", covariates=["x_squared", "x:a"]))
    assert "'x_squared'" in static and "'x:a'" in static
