from __future__ import annotations

from typing import Literal

from borges.analysis.models import AnalysisPlan, Judgement, Option, Step
from borges.analysis.option_equivalence import equivalence_reason
from borges.analysis.prompts.judge import build_messages
from borges.analysis.prompts.notes import describe_column_notes
from borges.analysis.schemas import JudgeOutput
from borges.llm.client import LLMClient, Role
from borges.telemetry import hooks

ACCEPT_THRESHOLD = 0.6
JudgeOrigin = Literal["planner", "adversary", "default"]


def judge_key(step: Step, option: Option, origin: JudgeOrigin) -> str:
    prefixes = {"planner": "judge:planner:", "default": "judge:default:"}
    return f"{prefixes.get(origin, 'judge:')}{step.id}.{option.id}"


async def judge_option(
    llm: LLMClient,
    plan: AnalysisPlan,
    step: Step,
    option: Option,
    origin: JudgeOrigin = "adversary",
) -> Judgement:
    duplicate = None if option.is_default else equivalence_reason(step, option)
    if duplicate is not None:
        hooks.audit(
            "judge.duplicate",
            decision="deny",
            reason=duplicate[:300],
            step_id=step.id,
            option_id=option.id,
            origin=origin,
        )
        return Judgement(
            defensibility=0.0,
            accepted=False,
            reason=f"equivalent to the conventional option: {duplicate}",
        )
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
