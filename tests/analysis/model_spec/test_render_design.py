from __future__ import annotations

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
