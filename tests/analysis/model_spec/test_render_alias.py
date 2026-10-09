from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from borges.analysis.model_spec.render import render_code
from tests.analysis.model_spec.data import make_spec


def run(code: str, data: pd.DataFrame) -> dict:
    namespace: dict = {}
    exec(code, namespace)
    return namespace["estimate"](data, {})


def wards(within: bool = False) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    ward = rng.choice(["A", "B", "C", "D"], 600)
    adopted = np.isin(ward, ["A", "B"]).astype(float)
    x = rng.integers(0, 2, 600).astype(float) if within else adopted
    risk = rng.poisson(np.where(adopted == 1, 3.2, 2.2)).astype(float)
    y = -0.4 * x + 0.3 * risk + (ward == "B") * 0.5 + rng.normal(size=600)
    return pd.DataFrame({"ward": ward, "x": x, "risk": risk, "y": y})


def test_a_categorical_that_rebuilds_the_exposure_by_itself_is_dropped_whole() -> None:
    data = wards()
    got = run(render_code(make_spec("ols", outcome="y", covariates=["ward", "risk"])), data)
    lean = run(render_code(make_spec("ols", outcome="y", covariates=["risk"])), data)
    assert got["note"] == ""
    assert got["estimate"] == pytest.approx(lean["estimate"], rel=1e-9)


def test_a_categorical_the_exposure_varies_within_is_kept() -> None:
    data = wards(within=True)
    got = run(render_code(make_spec("ols", outcome="y", covariates=["ward", "risk"])), data)
    lean = run(render_code(make_spec("ols", outcome="y", covariates=["risk"])), data)
    assert got["note"] == ""
    assert got["estimate"] != pytest.approx(lean["estimate"], rel=1e-6)
