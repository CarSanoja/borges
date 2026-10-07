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
from borges.analysis.planner_carried import carry_computed
from borges.analysis.planner_ctx_products import with_ctx_products
from borges.analysis.planner_degenerate import DEGENERATE, FRESH_TEMPERATURE, is_degenerate
from borges.analysis.planner_fidelity import faithful_plan
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
PLAN_RETRIES = 2
PLAN_TOKENS = 8192
FRESH_KEY = "planner:fresh"


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


async def _ask(
    llm: LLMClient, messages: list[dict[str, str]], key: str, temperature: float = 0.2
) -> PlannerOutput:
    response = await llm.complete(
        Role.PLANNER,
        messages,
        key=key,
        schema=PlannerOutput,
        max_tokens=PLAN_TOKENS,
        temperature=temperature,
    )
    return with_ctx_products(normalise_ids(PlannerOutput.model_validate(response.parsed)))


async def _broaden(
    llm: LLMClient,
    messages: list[dict[str, str]],
    out: PlannerOutput,
    profile: DatasetProfile,
    rule: DecisionRule,
    prefix: str = "planner",
) -> PlannerOutput:
    for attempt in range(PLAN_RETRIES):
        problems = plan_shortfalls(out.steps, profile, rule)
        if not problems:
            return out
        key = f"{prefix}:retry" if attempt == 0 else f"{prefix}:retry{attempt + 1}"
        try:
            out = await _ask(llm, build_retry_messages(messages, out, problems), key)
        except LLMError:
            return out
    return out


async def plan_analysis(
    llm: LLMClient, profile: DatasetProfile, question: str, rule: DecisionRule, analysis: str = ""
) -> AnalysisPlan:
    messages = build_messages(profile, question, rule, analysis)
    out = await _broaden(llm, messages, await _ask(llm, messages, "planner"), profile, rule)
    if is_degenerate(out.steps):
        try:
            fresh = await _ask(llm, messages, FRESH_KEY, FRESH_TEMPERATURE)
            out = await _broaden(llm, messages, fresh, profile, rule, FRESH_KEY)
        except LLMError:
            pass
    if is_degenerate(out.steps):
        raise LLMError(DEGENERATE)
    gaps: list[str] = []
    if analysis.strip():
        out, gaps = await faithful_plan(
            llm,
            messages,
            out,
            analysis,
            lambda retry, key: _ask(llm, retry, key),
            lambda fixed, prefix: _broaden(llm, messages, fixed, profile, rule, prefix),
        )
    taken: set[str] = set()
    planned = carry_computed(drop_renamed(drop_level_columns(out.steps, profile), profile), profile)
    steps = [_build_step(p, unique_id(p.id, taken)) for p in _order_model_last(planned)]
    plan = AnalysisPlan(
        question=question,
        estimand=out.estimand,
        decision_rule=rule,
        dataset=profile,
        steps=steps,
        result_scale=detect_scale(rule.metric),
        analysis=analysis,
        analysis_gaps=gaps,
    )
    return normalise_plan(plan)
