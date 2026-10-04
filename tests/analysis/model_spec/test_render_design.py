from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from borges.analysis.model_spec.render import render_code
from tests.analysis.model_spec.data import make_spec


def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "variant": ["treatment", "control", "treatment", "control", "treatment", "control"],
            "y": [3.0, 1.0, 4.0, 2.0, 5.0, 2.5],
        }
    )


def run(code: str, data: pd.DataFrame) -> dict:
    namespace: dict = {}
    exec(code, namespace)
    return namespace["estimate"](data, {})


def test_level_coding_is_applied_under_the_exposure_name() -> None:
    spec = make_spec("ols", outcome="y", exposure="variant", exposure_level="treatment")
    code = render_code(spec)
    assert "== 'treatment'" in code and "term = 'variant'" in code


def test_ols_on_a_level_coded_exposure_is_the_difference_in_means() -> None:
    data = frame()
    got = run(
        render_code(make_spec("ols", outcome="y", exposure="variant", exposure_level="treatment")),
        data,
    )
    treated = data.loc[data.variant == "treatment", "y"].mean()
    control = data.loc[data.variant == "control", "y"].mean()
    assert got["estimate"] == pytest.approx(treated - control, abs=1e-6)
    flipped = run(
        render_code(make_spec("ols", outcome="y", exposure="variant", exposure_level="control")),
        data,
    )
    assert flipped["estimate"] == pytest.approx(control - treated, abs=1e-6)


def test_no_level_leaves_the_numeric_template_unchanged() -> None:
    assert "== '" not in render_code(make_spec("ols"))


def aliased_frame() -> pd.DataFrame:
    rng = np.random.default_rng(3)
    year = rng.integers(1950, 2013, 200).astype(float)
    x = rng.normal(size=200)
    return pd.DataFrame(
        {
            "x": x,
            "year": year,
            "elapsed": 2013.0 - year,
            "w": rng.normal(size=200),
            "y": 1.5 * x + 0.02 * year + rng.normal(size=200),
        }
    )


def test_an_exactly_aliased_covariate_is_dropped_and_named() -> None:
    data = aliased_frame()
    full = make_spec("ols", outcome="y", covariates=["year", "elapsed", "w"])
    lean = make_spec("ols", outcome="y", covariates=["year", "w"])
    got, expected = run(render_code(full), data), run(render_code(lean), data)
    assert got["note"] == "aliased covariates dropped: elapsed"
    assert got["estimate"] == pytest.approx(expected["estimate"], rel=1e-9)
    assert got["ci_high"] == pytest.approx(expected["ci_high"], rel=1e-9)
    assert expected["note"] == ""


def test_a_covariate_aliased_with_the_exposure_is_dropped_instead_of_the_exposure() -> None:
    data = aliased_frame().assign(year=lambda d: d["x"] * 2.0)
    got = run(render_code(make_spec("ols", outcome="y", covariates=["year", "w"])), data)
    lean = run(render_code(make_spec("ols", outcome="y", covariates=["w"])), data)
    assert got["note"] == "aliased covariates dropped: year"
    assert got["estimate"] == pytest.approx(lean["estimate"], rel=1e-9)


def test_a_constant_exposure_is_kept_for_the_design_check_to_refuse() -> None:
    data = aliased_frame().assign(x=1.0)
    got = run(render_code(make_spec("ols", outcome="y", covariates=["w"])), data)
    assert got["note"] == ""


def test_covariates_that_rebuild_the_exposure_are_dropped_together() -> None:
    rng = np.random.default_rng(5)
    r1, r2 = rng.uniform(size=300), rng.uniform(size=300)
    data = pd.DataFrame({"r1": r1, "r2": r2, "w": rng.normal(size=300)})
    data["x"] = (data["r1"] + data["r2"]) / 2
    data["y"] = 2.0 * data["x"] + data["w"] + rng.normal(size=300)
    got = run(render_code(make_spec("ols", outcome="y", covariates=["r1", "r2", "w"])), data)
    lean = run(render_code(make_spec("ols", outcome="y", covariates=["w"])), data)
    assert got["note"] == (
        "aliased covariates dropped: r2; covariates that rebuild the exposure with them dropped: r1"
    )
    assert got["estimate"] == pytest.approx(lean["estimate"], rel=1e-9)


def test_a_numeric_binary_exposure_with_a_text_level_is_used_as_coded() -> None:
    data = frame().assign(variant=lambda f: (f.variant == "treatment").astype(int))
    spec = make_spec("ols", outcome="y", exposure="variant", exposure_level="treatment")
    got = run(render_code(spec), data)
    assert got["estimate"] == pytest.approx(4.0 - 1.8333333, rel=1e-6)


def test_a_level_that_is_not_a_value_of_the_exposure_fails_loudly() -> None:
    spec = make_spec("ols", outcome="y", exposure="variant", exposure_level="treated")
    with pytest.raises(ValueError, match="exposure level treated is not a value"):
        run(render_code(spec), frame())
