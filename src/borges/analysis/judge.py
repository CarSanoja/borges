from __future__ import annotations

from typing import Literal

from borges.analysis.models import AnalysisPlan, Judgement, Option, Step
from borges.analysis.prompts.judge import build_messages
from borges.analysis.prompts.notes import describe_column_notes
from borges.analysis.schemas import JudgeOutput
from borges.llm.client import LLMClient, Role

ACCEPT_THRESHOLD = 0.6
JudgeOrigin = Literal["planner", "adversary"]


def judge_key(step: Step, option: Option, origin: JudgeOrigin) -> str:
    prefix = "judge:planner:" if origin == "planner" else "judge:"
    return f"{prefix}{step.id}.{option.id}"


async def judge_option(
    llm: LLMClient,
    plan: AnalysisPlan,
    step: Step,
    option: Option,
    origin: JudgeOrigin = "adversary",
) -> Judgement:
    response = await llm.complete(
        Role.JUDGE,
        build_messages(plan, step, option, describe_column_notes(plan.dataset)),
        key=judge_key(step, option, origin),
        schema=JudgeOutput,
        max_tokens=800,
    )
    out = JudgeOutput.model_validate(response.parsed)
    return Judgement(
        defensibility=out.defensibility,
        accepted=out.accepted and out.defensibility >= ACCEPT_THRESHOLD,
        reason=out.reason,
        source=out.source,
    )
