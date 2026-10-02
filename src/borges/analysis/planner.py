from __future__ import annotations

import re

from borges.analysis.models import (
    AnalysisPlan,
    DatasetProfile,
    DecisionRule,
    Option,
    Step,
)
from borges.analysis.planner_validation import plan_shortfalls
from borges.analysis.prompts.planner import build_messages, build_retry_messages
from borges.analysis.result_scale import detect_scale
from borges.analysis.schemas import PlannedStep, PlannerOutput
from borges.llm.client import LLMClient, LLMError, Role


def clean_id(raw: str, fallback: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_]+", "_", raw.strip().lower()).strip("_")
    return cleaned or fallback


def normalise_ids(out: PlannerOutput) -> PlannerOutput:
    step_taken: set[str] = set()
    steps: list[PlannedStep] = []
    for si, step in enumerate(out.steps, 1):
        opt_taken: set[str] = set()
        options = [
            o.model_copy(update={"id": _unique(clean_id(o.id, f"option_{oi}"), opt_taken)})
            for oi, o in enumerate(step.options, 1)
        ]
        step_id = _unique(clean_id(step.id, f"step_{si}"), step_taken)
        steps.append(step.model_copy(update={"id": step_id, "options": options}))
    return out.model_copy(update={"steps": steps})


def _unique(candidate: str, taken: set[str]) -> str:
    value, n = candidate, 2
    while value in taken:
        value = f"{candidate}_{n}"
        n += 1
    taken.add(value)
    return value


def _build_step(planned: PlannedStep, step_id: str) -> Step:
    taken: set[str] = set()
    options: list[Option] = []
    default_seen = False
    for item in planned.options:
        is_default = item.is_default and not default_seen
        default_seen = default_seen or is_default
        options.append(
            Option(
                id=_unique(item.id, taken),
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
    return Step(
        id=step_id,
        title=planned.title,
        kind=planned.kind,
        description=planned.description,
        options=options,
        produces=[name.strip() for name in planned.produces if name.strip()],
    )


def _order_model_last(planned: list[PlannedStep]) -> list[PlannedStep]:
    model_steps = [s for s in planned if s.kind == "model"]
    if not model_steps:
        raise LLMError("planner returned no step of kind 'model'")
    final = model_steps[-1]
    return [s for s in planned if s is not final] + [final]


async def _ask(llm: LLMClient, messages: list[dict[str, str]], key: str) -> PlannerOutput:
    response = await llm.complete(
        Role.PLANNER, messages, key=key, schema=PlannerOutput, max_tokens=4096
    )
    return normalise_ids(PlannerOutput.model_validate(response.parsed))


async def _broaden(
    llm: LLMClient, messages: list[dict[str, str]], out: PlannerOutput, profile: DatasetProfile
) -> PlannerOutput:
    problems = plan_shortfalls(out.steps, profile)
    if not problems:
        return out
    try:
        return await _ask(llm, build_retry_messages(messages, out, problems), "planner:retry")
    except LLMError:
        return out


async def plan_analysis(
    llm: LLMClient, profile: DatasetProfile, question: str, rule: DecisionRule
) -> AnalysisPlan:
    messages = build_messages(profile, question, rule)
    out = await _broaden(llm, messages, await _ask(llm, messages, "planner"), profile)
    taken: set[str] = set()
    steps = [_build_step(p, _unique(p.id, taken)) for p in _order_model_last(out.steps)]
    return AnalysisPlan(
        question=question,
        estimand=out.estimand,
        decision_rule=rule,
        dataset=profile,
        steps=steps,
        result_scale=detect_scale(rule.metric),
    )
