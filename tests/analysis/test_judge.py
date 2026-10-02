from __future__ import annotations

import pytest

from borges.analysis.judge import judge_option
from borges.analysis.models import ColumnProfile, DatasetProfile
from borges.analysis.prompts.judge import build_messages
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


async def test_planner_origin_uses_its_own_key() -> None:
    out = JudgeOutput(defensibility=0.9, accepted=True, reason="r")
    llm = FakeLLM({"judge:planner:d1.trim": out})
    plan = make_plan()
    step = plan.step("d1")
    judgement = await judge_option(llm, plan, step, step.option("trim"), "planner")
    assert judgement.accepted is True
    assert llm.calls[0].key == "judge:planner:d1.trim"


def test_prompt_contains_the_column_notes_when_given() -> None:
    plan = make_plan()
    step = plan.step("d1")
    notes = "Column notes:\n- cnorm_1: positive indicator of norms"
    with_notes = build_messages(plan, step, step.option("trim"), notes)
    without = build_messages(plan, step, step.option("trim"))
    assert notes in with_notes[1]["content"]
    assert "Column notes" not in without[1]["content"]


async def test_judge_option_passes_the_plan_column_notes() -> None:
    out = JudgeOutput(defensibility=0.9, accepted=True, reason="r")
    llm = FakeLLM({"judge:d1.trim": out})
    plan = make_plan().model_copy(
        update={
            "dataset": DatasetProfile(
                name="d",
                n_rows=1,
                columns=[
                    ColumnProfile(
                        name="cnorm_1", dtype="int", n_missing=0, n_unique=3, note="a positive item"
                    )
                ],
            )
        }
    )
    step = plan.step("d1")
    await judge_option(llm, plan, step, step.option("trim"))
    assert "cnorm_1: a positive item" in llm.calls[0].messages[1]["content"]


def test_judge_prompt_rejects_linear_rescalings_of_the_conventional_option() -> None:
    from borges.analysis.prompts.judge import SYSTEM

    assert "only a linear rescaling of the conventional one" in SYSTEM
    assert "sum instead of a mean" in SYSTEM
    assert 'reason "equivalent to the conventional option"' in SYSTEM
