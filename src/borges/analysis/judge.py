from __future__ import annotations

from borges.analysis.models import AnalysisPlan, Judgement, Option, Step
from borges.analysis.prompts.judge import build_messages
from borges.analysis.schemas import JudgeOutput
from borges.llm.client import LLMClient, Role

ACCEPT_THRESHOLD = 0.6


async def judge_option(llm: LLMClient, plan: AnalysisPlan, step: Step, option: Option) -> Judgement:
    response = await llm.complete(
        Role.JUDGE,
        build_messages(plan, step, option),
        key=f"judge:{step.id}.{option.id}",
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
