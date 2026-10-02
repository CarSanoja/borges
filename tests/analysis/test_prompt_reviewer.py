from __future__ import annotations

from borges.analysis.prompts.reviewer import SYSTEM, build_messages
from borges.analysis.smoke_review import _payload
from borges.analysis.smoke_types import ReviewEntry
from tests.analysis.fakes import make_option, make_plan


def test_reviewer_flags_row_filters_inside_a_model_step() -> None:
    assert "other than complete cases" in SYSTEM
    assert "belongs to a filter step" in SYSTEM


def test_reviewer_flags_unit_mismatches_with_the_estimand() -> None:
    assert "unit mismatch" in SYSTEM
    assert "percentage points" in SYSTEM
    assert "unfaithful and must be flagged" in SYSTEM


def test_reviewer_receives_the_estimand_and_the_observed_smoke_estimate() -> None:
    plan = make_plan().model_copy(update={"estimand": "difference in percentage points"})
    option = make_option("trim")
    entry = ReviewEntry(option, None, {"estimate": -0.0014, "ci_low": -0.01, "ci_high": 0.01})
    payload = _payload(entry)
    assert payload["smoke_result"]["estimate"] == -0.0014
    content = build_messages(plan, plan.step("d1"), [payload])[1]["content"]
    assert "Estimand: difference in percentage points" in content
    assert "-0.0014" in content
