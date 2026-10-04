from __future__ import annotations

from pydantic import ValidationError

from borges.analysis.models import AnalysisPlan, Option, Step
from borges.analysis.planner import normalise_ids, unique_id
from borges.analysis.prompts.replan import build_replan_messages
from borges.analysis.schemas import PlannedStep, PlannerOutput, ReplanOutput
from borges.analysis.smoke_types import Outcome
from borges.llm.client import LLMClient, LLMError, Role


def replan_key(step_id: str) -> str:
    return f"planner:replan:{step_id}"


def _failures(outcomes: list[Outcome]) -> list[tuple[str, str, str, str]]:
    return [
        (o.option.id, o.option.label, o.option.spec, o.error or (o.errors[-1] if o.errors else ""))
        for o in outcomes
    ]


def _options(
    step: Step, planned: ReplanOutput, plan: AnalysisPlan, taken: set[str]
) -> list[Option]:
    shell = PlannedStep(
        id=step.id,
        title=step.title,
        kind=step.kind,
        description=step.description,
        options=planned.options,
        produces=step.produces,
    )
    normalised = normalise_ids(PlannerOutput(estimand=plan.estimand, steps=[shell])).steps[0]
    options: list[Option] = []
    default_seen = False
    for item in normalised.options:
        is_default = item.is_default and not default_seen
        default_seen = default_seen or is_default
        options.append(
            Option(
                id=unique_id(item.id, taken),
                label=item.label,
                rationale=item.rationale,
                spec=item.spec,
                is_default=is_default,
                origin="planner",
                source=item.source,
            )
        )
    if not default_seen:
        options[0].is_default = True
    return options


async def propose_options(
    llm: LLMClient, plan: AnalysisPlan, step: Step, outcomes: list[Outcome]
) -> list[Option] | None:
    messages = build_replan_messages(plan, step, _failures(outcomes))
    try:
        response = await llm.complete(
            Role.PLANNER, messages, key=replan_key(step.id), schema=ReplanOutput, max_tokens=4096
        )
        planned = ReplanOutput.model_validate(response.parsed)
    except (LLMError, ValidationError):
        return None
    failed = {o.option.id for o in outcomes}
    return _options(step, planned, plan, set(failed))
