from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import statsmodels.formula.api as smf

from borges.analysis.model_spec.render import render_code
from borges.analysis.model_spec.validate_exposure import moderator_problems
from borges.analysis.models import ColumnProfile, DatasetProfile
from tests.analysis.model_spec.data import make_spec


def frame() -> pd.DataFrame:
    rng = np.random.default_rng(11)
    n = 400
    fertile = rng.integers(0, 2, n).astype(float)
    status = rng.choice(["committed", "single"], n)
    committed = (status == "committed").astype(float)
    religiosity = 5 + 0.8 * fertile * committed - 0.6 * fertile + rng.normal(0, 1, n)
    return pd.DataFrame({"fertile": fertile, "rel_status": status, "religiosity": religiosity})


def run(spec_kwargs: dict, data: pd.DataFrame) -> dict:
    namespace: dict = {}
    exec(render_code(make_spec("ols", **spec_kwargs)), namespace)
    return namespace["estimate"](data, {})


def interaction(level: str) -> dict:
    return {
        "outcome": "religiosity",
        "exposure": "fertile",
        "moderator": "rel_status",
        "moderator_level": level,
    }


def test_the_named_moderator_level_sets_the_sign_of_the_interaction() -> None:
    data = frame()
    reference = smf.ols(
        "religiosity ~ fertile * I((rel_status == 'committed').astype(float))", data
    ).fit()
    expected = reference.params.iloc[-1]
    got = run(interaction("committed"), data)
    assert got["estimate"] == pytest.approx(expected, abs=1e-6)
    assert got["estimate"] > 0
    assert run(interaction("single"), data)["estimate"] == pytest.approx(-expected, abs=1e-6)


def test_a_text_moderator_without_a_level_fails_with_the_reason() -> None:
    spec = {"outcome": "religiosity", "exposure": "fertile", "moderator": "rel_status"}
    with pytest.raises(ValueError, match="moderator_level"):
        run(spec, frame())


def profile(dtype: str) -> DatasetProfile:
    column = ColumnProfile(
        name="rel_status",
        dtype=dtype,
        n_missing=0,
        n_unique=2,
        summary={"top_1": "committed: 120", "top_2": "single: 98"},
    )
    return DatasetProfile(name="fertility", n_rows=218, columns=[column])


def test_validation_asks_for_a_listed_level_of_a_text_moderator() -> None:
    base = make_spec("ols", outcome="religiosity", exposure="fertile", moderator="rel_status")
    [missing] = moderator_problems(base, profile("object"))
    assert "set moderator_level" in missing and "committed" in missing
    wrong = base.model_copy(update={"moderator_level": "married"})
    assert "not a listed level" in moderator_problems(wrong, profile("object"))[0]
    right = base.model_copy(update={"moderator_level": "committed"})
    assert moderator_problems(right, profile("object")) == []
    assert "must not be set" in moderator_problems(right, profile("int64"))[0]
