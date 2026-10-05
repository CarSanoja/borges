from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from borges.analysis.model_spec.normalise import normalise_spec
from borges.analysis.model_spec.render import render_code
from borges.analysis.model_spec.validate_exposure import exposure_problems
from tests.analysis.model_spec.data import make_spec

TEXT = (
    "Create binary exposure: dark = 1 if skin_tone >= 0.5 else 0. Fit Poisson regression with "
    "formula: redCards ~ dark + {covariates}, offset=log(games)."
)
AVAILABLE = ["redCards", "games", "skin_tone", "refNum"]


def tones() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    tone = rng.choice([0.0, 0.25, 0.375, 0.5, 0.625, 0.75, 1.0], size=400)
    tone[:40] = np.nan
    y = (tone >= 0.5).astype(float) * 2.0 + rng.normal(size=400)
    return pd.DataFrame({"y": y, "skin_tone": tone})


def run(spec, data: pd.DataFrame) -> dict:
    namespace: dict = {}
    exec(render_code(spec), namespace)
    return namespace["estimate"](data, {})


@pytest.mark.parametrize("exposure, level", [("dark", None), ("skin_tone", "0.5")])
def test_a_stated_cut_becomes_the_column_and_its_threshold(exposure: str, level) -> None:
    spec = make_spec("poisson", outcome="redCards", exposure=exposure, exposure_level=level)
    fixed = normalise_spec(spec, TEXT, AVAILABLE, None)
    assert (fixed.exposure, fixed.exposure_threshold, fixed.exposure_level) == (
        "skin_tone",
        0.5,
        None,
    )


def test_the_template_cuts_after_dropping_missing_rows() -> None:
    data = tones()
    result = run(make_spec("ols", outcome="y", exposure="skin_tone", exposure_threshold=0.5), data)
    kept = data.dropna()
    expected = (
        kept.loc[kept.skin_tone >= 0.5, "y"].mean() - kept.loc[kept.skin_tone < 0.5, "y"].mean()
    )
    assert result["n"] == 360
    assert result["estimate"] == pytest.approx(expected, rel=1e-9)


def test_an_exact_level_of_a_fractional_numeric_column_is_refused() -> None:
    spec = make_spec("ols", outcome="y", exposure="skin_tone", exposure_level="0.5")
    with pytest.raises(ValueError, match="fractional values"):
        run(spec, tones())


def test_a_threshold_with_a_level_is_a_problem() -> None:
    spec = make_spec("ols", outcome="y", exposure="x", exposure_level="1", exposure_threshold=0.5)
    assert exposure_problems(spec, None) == [
        "set exposure_level for a text exposure or exposure_threshold for a cut, not both"
    ]
