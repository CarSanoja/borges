from __future__ import annotations

import re

from borges.analysis.code_guard_ctx import CTX_WRITE
from borges.analysis.ids import slug_id
from borges.analysis.models import (
    AnalysisPlan,
    DatasetProfile,
    DecisionRule,
    Option,
    Step,
)
from borges.analysis.option_references import normalise_plan
from borges.analysis.planner_products import drop_level_columns, drop_renamed
from borges.analysis.planner_validation import plan_shortfalls, reads_the_result
from borges.analysis.prompts.planner import build_messages, build_retry_messages
from borges.analysis.result_scale import detect_scale
from borges.analysis.schemas import PlannedStep, PlannerOutput
from borges.llm.client import LLMClient, LLMError, Role

CTX_REFERENCE = re.compile(
    r"""^ctx\s*(?:\[\s*["']?([^"'\]]+?)["']?\s*\]?|\.get\(\s*["']([^"']+)["'][^)]*\)|[.:|/]\s*(.+))$"""
)


def produced_name(raw: str) -> str:
    name = raw.strip()
    match = CTX_REFERENCE.match(name)
    if match is None:
        return name
    return next(group for group in match.groups() if group).strip()


BARE_CTX = frozenset({"ctx", "context"})


def step_produces(planned: PlannedStep) -> list[str]:
    names = [produced_name(name) for name in planned.produces]
    if any(name.lower() in BARE_CTX for name in names):
        written = [{key for key, _ in CTX_WRITE.findall(o.spec)} for o in planned.options]
        shared = sorted(set.intersection(*written)) if written else []
        names = [key for name in names for key in (shared if name.lower() in BARE_CTX else [name])]
    return list(dict.fromkeys(filter(None, names)))


def clean_id(raw: str, fallback: str) -> str:
    cleaned = slug_id(raw)
    return cleaned or fallback


def normalise_ids(out: PlannerOutput) -> PlannerOutput:
    step_taken: set[str] = set()
    steps: list[PlannedStep] = []
    for si, step in enumerate(out.steps, 1):
        opt_taken: set[str] = set()
        options = [
            o.model_copy(update={"id": unique_id(clean_id(o.id, f"option_{oi}"), opt_taken)})
            for oi, o in enumerate(step.options, 1)
        ]
        step_id = unique_id(clean_id(step.id, f"step_{si}"), step_taken)
        steps.append(step.model_copy(update={"id": step_id, "options": options}))
    return out.model_copy(update={"steps": steps})


def unique_id(candidate: str, taken: set[str]) -> str:
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
    return Step(
        id=step_id,
        title=planned.title,
        kind=planned.kind,
        description=planned.description,
        options=options,
        produces=step_produces(planned),
    )


def _order_model_last(planned: list[PlannedStep]) -> list[PlannedStep]:
    model_steps = [s for s in planned if s.kind == "model"]
    if not model_steps:
        raise LLMError("planner returned no step of kind 'model'")
    final = model_steps[0]
    if len(model_steps) > 1:
        seen = {o.id for o in final.options}
        extra = []
        for step in model_steps[1:]:
            for option in step.options:
                if option.id not in seen:
                    seen.add(option.id)
                    extra.append(option.model_copy(update={"is_default": False}))
        final = final.model_copy(update={"options": [*final.options, *extra]})
    dropped = set(reads_the_result(planned))
    return [s for s in planned if s.kind != "model" and s.id not in dropped] + [final]


async def _ask(llm: LLMClient, messages: list[dict[str, str]], key: str) -> PlannerOutput:
    response = await llm.complete(
        Role.PLANNER, messages, key=key, schema=PlannerOutput, max_tokens=4096
    )
    return normalise_ids(PlannerOutput.model_validate(response.parsed))


async def _broaden(
    llm: LLMClient,
    messages: list[dict[str, str]],
    out: PlannerOutput,
    profile: DatasetProfile,
    rule: DecisionRule,
) -> PlannerOutput:
    problems = plan_shortfalls(out.steps, profile, rule)
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
    out = await _broaden(llm, messages, await _ask(llm, messages, "planner"), profile, rule)
    taken: set[str] = set()
    planned = drop_renamed(drop_level_columns(out.steps, profile), profile)
    steps = [_build_step(p, unique_id(p.id, taken)) for p in _order_model_last(planned)]
    plan = AnalysisPlan(
        question=question,
        estimand=out.estimand,
        decision_rule=rule,
        dataset=profile,
        steps=steps,
        result_scale=detect_scale(rule.metric),
    )
    return normalise_plan(plan)
