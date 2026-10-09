from __future__ import annotations

from typing import Literal

from borges.analysis.models import AnalysisPlan, Judgement, Option, Step
from borges.analysis.option_columns import missing_reason
from borges.analysis.option_equivalence import equivalence_reason
from borges.analysis.prompts.judge import build_messages
from borges.analysis.prompts.notes import describe_column_notes, describe_named_columns
from borges.analysis.schemas import JudgeOutput
from borges.llm.client import LLMClient, Role
from borges.telemetry import hooks

ACCEPT_THRESHOLD = 0.6
JudgeOrigin = Literal["planner", "adversary", "default"]


def judge_key(step: Step, option: Option, origin: JudgeOrigin) -> str:
    prefixes = {"planner": "judge:planner:", "default": "judge:default:"}
    return f"{prefixes.get(origin, 'judge:')}{step.id}.{option.id}"


def judge_facts(plan: AnalysisPlan, option: Option) -> str:
    text = " ".join([option.label, option.rationale, option.spec])
    blocks = [describe_column_notes(plan.dataset), describe_named_columns(plan.dataset, text)]
    return "\n".join(b for b in blocks if b)


async def judge_option(
    llm: LLMClient,
    plan: AnalysisPlan,
    step: Step,
    option: Option,
    origin: JudgeOrigin = "adversary",
) -> Judgement:
    absent = None if option.is_default else missing_reason(plan, option)
    if absent is not None:
        hooks.audit(
            "judge.missing_columns",
            decision="deny",
            reason=absent[:300],
            step_id=step.id,
            option_id=option.id,
            origin=origin,
        )
        return Judgement(defensibility=0.0, accepted=False, reason=absent)
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
        build_messages(plan, step, option, judge_facts(plan, option)),
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
