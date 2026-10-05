from __future__ import annotations

from borges.analysis.coder import _smoke_repair
from borges.analysis.models import AnalysisPlan, Option, Step
from borges.analysis.prompts.reviewer import build_messages
from borges.analysis.schemas import ReviewerOutput, ReviewVerdict
from borges.llm.client import LLMClient, LLMError, Role
from borges.runs.emitter import RunEmitter
from borges.runs.events import OptionReviewedData


def _payload(option: Option) -> dict[str, object]:
    return {
        "option_id": option.id,
        "label": option.label,
        "spec": option.spec,
        "code": option.code,
        "effects": None,
    }


async def review_verdict(
    llm: LLMClient, plan: AnalysisPlan, emitter: RunEmitter, step: Step, option: Option, key: str
) -> ReviewVerdict | None:
    try:
        response = await llm.complete(
            Role.REVIEWER,
            build_messages(plan, step, [_payload(option)]),
            key=key,
            schema=ReviewerOutput,
            max_tokens=1000,
        )
    except LLMError:
        return None
    verdicts = ReviewerOutput.model_validate(response.parsed).verdicts
    verdict = next((v for v in verdicts if v.option_id == option.id), None)
    if verdict is None:
        return None
    data = OptionReviewedData(
        step_id=step.id,
        option_id=option.id,
        faithful=verdict.faithful,
        changes_estimand=verdict.changes_estimand,
        problem=verdict.problem,
        model=response.usage.model,
    )
    await emitter.emit("option.reviewed", data.model_dump(mode="json"))
    return verdict


async def review_proposal(
    llm: LLMClient, plan: AnalysisPlan, emitter: RunEmitter, step: Step, option: Option
) -> Option | None:
    """Review an adversary option's code against its spec; repair once, drop a new question."""
    key = f"reviewer:adversary:{step.id}:{option.id}"
    verdict = await review_verdict(llm, plan, emitter, step, option, key)
    if verdict is None:
        return option
    if verdict.changes_estimand:
        return None
    if verdict.faithful:
        return option
    problem = verdict.problem or "the code does not do what the spec says"
    try:
        code, violation, _ = await _smoke_repair(llm, plan, step, option, problem, 1)
    except LLMError:
        return None
    if violation is not None:
        return None
    return option.model_copy(update={"code": code})
