from __future__ import annotations

import itertools

import pandas as pd
import pytest

from borges.analysis.code_guard import check_code
from borges.analysis.model_spec.render import render_code
from borges.analysis.model_spec.schema import ModelSpecOutput
from tests.analysis.model_spec.data import make_spec, synthetic
from tests.analysis.model_spec.reference import reference

FRAME = synthetic()
COV_TYPES = ("nonrobust", "HC0", "HC1", "HC2", "HC3", "cluster")
REPORTS = {
    "ols": ("coefficient",),
    "logit": ("coefficient", "odds_ratio"),
    "poisson": ("coefficient", "rate_ratio"),
    "negbin": ("coefficient", "rate_ratio"),
}
GRID = [
    (family, cov, report, moderated)
    for family, reports in REPORTS.items()
    for cov, report, moderated in itertools.product(COV_TYPES, reports, (False, True))
]


def run(spec: ModelSpecOutput, frame: pd.DataFrame, ctx: dict) -> dict:
    namespace: dict = {}
    exec(render_code(spec), namespace)
    return namespace["estimate"](frame, ctx)


def assert_matches(spec: ModelSpecOutput, ctx: dict | None = None) -> dict:
    ctx = ctx if ctx is not None else {}
    expected = reference(spec, FRAME, ctx)
    got = run(spec, FRAME.copy(), dict(ctx))
    for key in ("estimate", "ci_low", "ci_high", "p_value"):
        assert got[key] == pytest.approx(expected[key], rel=1e-8, abs=1e-12), key
    assert got["n"] == expected["n"]
    assert got["ci_low"] < got["estimate"] < got["ci_high"]
    assert 0.0 <= got["p_value"] <= 1.0
    return got


def fields(cov: str, report: str, moderated: bool) -> dict:
    extra: dict = {"cov_type": cov, "report": report, "covariates": ["a"]}
    if cov == "cluster":
        extra["cluster"] = "g"
    if moderated:
        extra["moderator"] = "m"
    return extra


@pytest.mark.parametrize(("family", "cov", "report", "moderated"), GRID)
def test_rendered_code_matches_a_direct_fit(family, cov, report, moderated) -> None:
    spec = make_spec(family, **fields(cov, report, moderated))
    assert_matches(spec)
    assert check_code(render_code(spec), "model", f"{cov} robust standard errors") == []


@pytest.mark.parametrize("family", list(REPORTS))
def test_ctx_covariates_categorical_standardize_and_offset(family) -> None:
    extra: dict = {"covariates": ["a"], "covariates_from_ctx": True, "moderator": "m"}
    if family in ("poisson", "negbin"):
        extra["offset_log"] = "games"
    if family == "ols":
        extra["standardize"] = ["y_cont", "x", "m"]
    else:
        extra["standardize"] = ["m"]
    spec = make_spec(family, **extra)
    assert_matches(spec, {"covariates": ["cat", "a", "x"]})
    assert check_code(render_code(spec), "model") == []


def test_offset_changes_the_count_estimate() -> None:
    with_offset = make_spec("poisson", offset_log="games", report="rate_ratio")
    without = make_spec("poisson", report="rate_ratio")
    assert assert_matches(with_offset)["estimate"] != assert_matches(without)["estimate"]


def test_ratio_report_exposes_the_coefficient() -> None:
    got = run(make_spec("logit", report="odds_ratio"), FRAME.copy(), {})
    plain = run(make_spec("logit"), FRAME.copy(), {})
    assert got["extra"]["coefficient"] == pytest.approx(plain["estimate"])
    assert "extra" not in plain


def test_missing_ctx_covariates_are_ignored() -> None:
    spec = make_spec("ols", covariates_from_ctx=True)
    assert run(spec, FRAME.copy(), {})["n"] == len(FRAME.dropna(subset=["y_cont", "x"]))


def test_rendering_is_deterministic_and_leaves_the_input_untouched() -> None:
    spec = make_spec("negbin", standardize=["x"], covariates=["cat"])
    assert render_code(spec) == render_code(spec)
    before = FRAME.copy()
    run(spec, FRAME, {})
    pd.testing.assert_frame_equal(FRAME, before)


def test_rendered_code_never_selects_rows_by_value_or_builds_keys() -> None:
    code = render_code(make_spec("logit", moderator="m", covariates_from_ctx=True))
    assert ".query(" not in code and "isin(" not in code and "== " not in code
    assert 'df["' not in code and "ctx[" not in code
