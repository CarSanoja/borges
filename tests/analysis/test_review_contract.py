from __future__ import annotations

import pytest

from borges.analysis.review_contract import IGNORED, apply_unit_contract
from borges.analysis.schemas import ReviewVerdict


def verdict(problem: str, faithful: bool = False) -> ReviewVerdict:
    return ReviewVerdict(option_id="o", faithful=faithful, changes_estimand=False, problem=problem)


@pytest.mark.parametrize(
    "problem",
    [
        "The spec requires returning ATE in percentage points (value * 100), but the code returns "
        "the raw coefficient from OLS (value) without multiplying by 100.",
        "The spec returns teff*100, ci_low*100, ci_high*100 (percentage points).",
        "Estimates should be multiplied by 100.",
    ],
)
def test_unit_demands_alone_are_dropped(problem: str) -> None:
    out = apply_unit_contract(verdict(problem))
    assert out.faithful and out.problem == IGNORED


def test_a_real_problem_next_to_a_unit_demand_survives() -> None:
    out = apply_unit_contract(
        verdict(
            "The spec requires HC0 standard errors, but the code uses cov_type='HC1'. "
            "The spec also returns teff*100, ci_low*100, ci_high*100 (percentage points)."
        )
    )
    assert not out.faithful
    assert out.problem == "The spec requires HC0 standard errors, but the code uses cov_type='HC1'."


@pytest.mark.parametrize(
    "problem",
    [
        "The keep-all filter dropped 1000 rows of the control group.",
        "The spec names a cluster-robust estimator but the code fits plain OLS.",
    ],
)
def test_other_problems_are_untouched(problem: str) -> None:
    assert apply_unit_contract(verdict(problem)) == verdict(problem)


def test_faithful_verdicts_are_untouched() -> None:
    assert apply_unit_contract(verdict("", faithful=True)) == verdict("", faithful=True)
