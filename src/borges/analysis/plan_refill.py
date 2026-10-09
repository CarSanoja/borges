from __future__ import annotations

from pydantic import ValidationError

from borges.analysis.models import AnalysisPlan, Option, Step
from borges.analysis.option_references import expand_option
from borges.analysis.planner import clean_id, unique_id
from borges.analysis.planner_products import other_names
from borges.analysis.planner_validation import MIN_BRANCHING_STEPS
from borges.analysis.prompts.refill import build_refill_messages
from borges.analysis.schemas import ReplanOutput
from borges.llm.client import LLMClient, LLMError, Role

MAX_REFILL_OPTIONS = 2
Rejected = list[tuple[Option, str]]


def refill_key(step_id: str, failed: bool = False) -> str:
    return f"planner:refill{'-code' if failed else ''}:{step_id}"


def collapsed_steps(plan: AnalysisPlan, before: dict[str, int]) -> list[Step]:
    """Steps the judge or the coder left with one option, when that leaves the plan too few
    branching steps."""
    was = sum(1 for count in before.values() if count > 1)
    now = sum(1 for step in plan.steps if len(step.options) > 1)
    if was < MIN_BRANCHING_STEPS or now >= MIN_BRANCHING_STEPS:
        return []
    return [s for s in plan.steps if before.get(s.id, 0) > 1 and len(s.options) == 1]


def _signature(spec: str) -> str:
    return " ".join(spec.lower().split())


async def propose_refill(
    llm: LLMClient, plan: AnalysisPlan, step: Step, rejected: Rejected, failed: bool = False
) -> list[Option]:
    """New non-default alternatives for a step whose alternatives the judge all rejected, or
    (failed) whose alternatives all failed to run."""
    messages = build_refill_messages(plan, step, rejected, failed)
    key = refill_key(step.id, failed)
    try:
        response = await llm.complete(
            Role.PLANNER, messages, key=key, schema=ReplanOutput, max_tokens=4096
        )
        planned = ReplanOutput.model_validate(response.parsed)
    except (LLMError, ValidationError):
        return []
    seen = {_signature(o.spec) for o in step.options} | {_signature(o.spec) for o, _ in rejected}
    taken = {o.id for o in step.options} | {o.id for o, _ in rejected}
    columns = {c.name for c in plan.dataset.columns}
    fresh = [
        item
        for item in planned.options
        if _signature(item.spec) not in seen and not other_names(step, item.spec, columns)
    ]
    options = [
        Option(
            id=unique_id(clean_id(item.id, "option"), taken),
            label=item.label,
            rationale=item.rationale,
            spec=item.spec,
            is_default=False,
            origin="planner",
            source=item.source,
        )
        for item in fresh[:MAX_REFILL_OPTIONS]
    ]
    shell = step.model_copy(update={"options": [*step.options, *options]})
    scope = plan.model_copy(update={"steps": [shell if s.id == step.id else s for s in plan.steps]})
    return [expand_option(scope, shell, o) for o in options]
