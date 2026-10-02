from __future__ import annotations

from typing import Any

import pytest

from borges.analysis import coder
from borges.analysis.schemas import ReviewerOutput, ReviewVerdict
from borges.runs.adversary_review import review_proposal
from tests.analysis.fakes import FakeLLM
from tests.runs.fakes import adversary_proposal, make_plan

KEY = "reviewer:adversary:s2:adv"


class Emitter:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        self.events.append((event_type, data))


def _verdict(faithful: bool, changes: bool = False, problem: str = "") -> ReviewerOutput:
    return ReviewerOutput(
        verdicts=[
            ReviewVerdict(
                option_id="adv", faithful=faithful, changes_estimand=changes, problem=problem
            )
        ]
    )


def _option() -> Any:
    return adversary_proposal().option.model_copy(
        update={"code": "def apply(df, ctx):\n    return df\n"}
    )


async def test_faithful_option_is_kept_and_reported() -> None:
    plan, emitter = make_plan(), Emitter()
    llm = FakeLLM({KEY: _verdict(True)})
    option = _option()
    kept = await review_proposal(llm, plan, emitter, plan.step("s2"), option)
    assert kept == option
    assert emitter.events[0][0] == "option.reviewed"
    assert emitter.events[0][1]["faithful"] is True


async def test_option_that_changes_the_question_is_dropped() -> None:
    plan = make_plan()
    llm = FakeLLM({KEY: _verdict(False, changes=True, problem="swaps the groups")})
    assert await review_proposal(llm, plan, Emitter(), plan.step("s2"), _option()) is None


async def test_unfaithful_option_is_repaired_with_the_problem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = make_plan()
    seen: list[str] = []

    async def repair(llm: Any, plan: Any, step: Any, option: Any, error: str, attempt: int):
        seen.append(error)
        return "def apply(df, ctx):\n    return df.copy()\n", None, "fake"

    monkeypatch.setattr("borges.runs.adversary_review._smoke_repair", repair)
    problem = "spec says negative binomial; the code fits a Poisson family"
    llm = FakeLLM({KEY: _verdict(False, problem=problem)})
    fixed = await review_proposal(llm, plan, Emitter(), plan.step("s2"), _option())
    assert seen == [problem]
    assert fixed is not None and "df.copy()" in (fixed.code or "")
    assert coder is not None


async def test_missing_reviewer_keeps_the_option() -> None:
    plan = make_plan()
    option = _option()
    assert await review_proposal(FakeLLM({}), plan, Emitter(), plan.step("s2"), option) == option
