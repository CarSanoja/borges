from __future__ import annotations

import pytest

from borges.analysis.judge import judge_option
from borges.analysis.schemas import JudgeOutput
from borges.llm.client import Role
from tests.analysis.fakes import FakeLLM, make_plan


@pytest.mark.parametrize(
    ("score", "claimed", "expected"),
    [
        (0.59, True, False),
        (0.6, True, True),
        (0.95, True, True),
        (0.95, False, False),
        (0.1, True, False),
    ],
)
async def test_acceptance_is_enforced(score: float, claimed: bool, expected: bool) -> None:
    out = JudgeOutput(defensibility=score, accepted=claimed, reason="r", source="S")
    llm = FakeLLM({"judge:d1.trim": out})
    plan = make_plan()
    step = plan.step("d1")
    judgement = await judge_option(llm, plan, step, step.option("trim"))
    assert judgement.accepted is expected
    assert judgement.defensibility == score
    assert judgement.source == "S" and judgement.reason == "r"
    call = llm.calls[0]
    assert call.role is Role.JUDGE and call.max_tokens == 800 and call.schema is JudgeOutput
    assert "Spec for trim" in call.messages[1]["content"]


async def test_model_rejection_wins_over_high_score() -> None:
    out = JudgeOutput(defensibility=0.9, accepted=False, reason="changes the estimand")
    llm = FakeLLM({"judge:d1.trim": out})
    plan = make_plan()
    step = plan.step("d1")
    judgement = await judge_option(llm, plan, step, step.option("trim"))
    assert judgement.accepted is False
