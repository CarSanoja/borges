from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from borges.analysis.code_guard import check_code
from borges.analysis.code_guard_statsmodels import option_intent
from borges.analysis.coder_normalise import add_missing_imports, strip_trailing_closer
from borges.analysis.coder_recode import fresh_recode
from borges.analysis.coder_replan import make_replan
from borges.analysis.coder_smoke import SmokeConfig, smoke_plan
from borges.analysis.model_spec.request import join_notes, request_template, template_family
from borges.analysis.models import AnalysisPlan, CodingSummary, Option, Step
from borges.analysis.prompts.coder import build_messages
from borges.analysis.schemas import CoderOutput
from borges.llm.client import LLMClient, LLMError, Role
from borges.llm.gather import gather_cancelling
from borges.telemetry.scopes import option_span

NORMALISED_NOTE = "removed a stray closing-bracket line at the end of the code"
OnCoded = Callable[[str, str, bool, int, str | None, list[str]], Awaitable[None]]


async def _request_code(
    llm: LLMClient,
    plan: AnalysisPlan,
    step: Step,
    option: Option,
    error: str | None = None,
    suffix: str = ":repair",
    models: list[str] | None = None,
    notes: list[str] | None = None,
) -> str:
    key = f"coder:{step.id}.{option.id}" + (suffix if error is not None else "")
    response = await llm.complete(
        Role.CODER if error is None else Role.REPAIRER,
        build_messages(plan, step, option, error),
        key=key,
        schema=CoderOutput,
        max_tokens=1500,
    )
    if models is not None:
        models.append(response.usage.model)
    code, closed = strip_trailing_closer(CoderOutput.model_validate(response.parsed).code)
    code, imported = add_missing_imports(code)
    if (closed or imported) and notes is not None:
        notes.append(NORMALISED_NOTE)
    return code


async def generate_checked(
    llm: LLMClient,
    plan: AnalysisPlan,
    step: Step,
    option: Option,
    models: list[str] | None = None,
) -> tuple[str | None, int, str | None]:
    notes: list[str] = []
    skips: list[str] = []
    if step.kind == "model":
        templated = await request_template(llm, plan, step, option, models, skips)
        if templated is not None:
            return templated.code, 1, templated.note
    code = await _request_code(llm, plan, step, option, models=models, notes=notes)
    violations = check_code(code, step.kind, option_intent(option))
    if not violations:
        return code, 1, join_notes(skips, notes)
    error = "\n".join(violations)
    draft = option.model_copy(update={"code": code})
    code = await _request_code(llm, plan, step, draft, error, models=models, notes=notes)
    violations = check_code(code, step.kind, option_intent(option))
    if not violations:
        return code, 2, join_notes(skips, notes)
    errors = [error, "\n".join(violations)]
    try:
        code, problem, model = await fresh_recode(llm, plan, step, option, errors, ":guard_recode")
    except LLMError:
        return None, 2, errors[-1]
    if models is not None:
        models.append(model)
    if problem is None:
        return code, 3, join_notes(skips, notes)
    return None, 3, problem


async def code_option(llm: LLMClient, plan: AnalysisPlan, step: Step, option: Option) -> str:
    """Code one option, passing the code guard with one repair attempt, or raise LLMError."""
    code, _, error = await generate_checked(llm, plan, step, option)
    if code is None:
        raise LLMError(f"code for {step.id}.{option.id} violates the guard: {error}")
    return code


async def _smoke_repair(
    llm: LLMClient, plan: AnalysisPlan, step: Step, option: Option, error: str, attempt: int
) -> tuple[str, str | None, str]:
    models: list[str] = []
    code = await _request_code(
        llm, plan, step, option, error, suffix=f":smoke{attempt}", models=models
    )
    violations = check_code(code, step.kind, option_intent(option))
    return code, ("\n".join(violations) if violations else None), models[0]


async def code_plan(
    llm: LLMClient,
    plan: AnalysisPlan,
    on_coded: OnCoded | None = None,
    concurrency: int = 6,
    smoke: SmokeConfig | None = None,
    summary: CodingSummary | None = None,
) -> AnalysisPlan:
    semaphore = asyncio.Semaphore(concurrency)

    models_by_option: dict[tuple[str, str], list[str]] = {}

    async def work(step: Step, option: Option) -> tuple[str | None, int, str | None]:
        models = models_by_option.setdefault((step.id, option.id), [])
        async with semaphore:
            with option_span("option.code", step.id, option.id) as span:
                try:
                    code, attempts, error = await generate_checked(llm, plan, step, option, models)
                except LLMError as exc:
                    code, attempts, error = None, 1, str(exc)
                span.set_attribute("borges.option.ok", code is not None)
                span.set_attribute("borges.option.attempts", attempts)
                family = template_family(error)
                if family is not None:
                    span.set_attribute("borges.option.template", family)
        if on_coded is not None:
            await on_coded(step.id, option.id, code is not None, attempts, error, models)
        return code, attempts, error

    pending = [(s, o) for s in plan.steps for o in s.options if o.code is None]
    results = await gather_cancelling(work(s, o) for s, o in pending)

    coded = plan.model_copy(deep=True)
    failed_defaults: dict[str, tuple[str, str | None]] = {}
    attempts_by_option: dict[tuple[str, str], int] = {}
    for (step, option), (code, attempts, error) in zip(pending, results, strict=True):
        target = coded.step(step.id)
        attempts_by_option[(step.id, option.id)] = attempts
        if code is not None:
            target.option(option.id).code = code
            continue
        if option.is_default:
            failed_defaults[step.id] = (option.id, error)
        target.options = [o for o in target.options if o.id != option.id]
    for step_id, (default_id, error) in failed_defaults.items():
        await _promote_sibling(
            coded, step_id, default_id, error, attempts_by_option, models_by_option, on_coded
        )
    if summary is not None:
        summary.options += len(pending)
        summary.failed += sum(1 for code, _, _ in results if code is None)
    if smoke is None:
        return coded

    async def repair(
        step: Step, option: Option, error: str, attempt: int
    ) -> tuple[str, str | None, str]:
        return await _smoke_repair(llm, coded, step, option, error, attempt)

    async def recode(step: Step, option: Option, errors: list[str]) -> tuple[str, str | None, str]:
        return await fresh_recode(llm, coded, step, option, errors)

    replan = make_replan(llm, coded, generate_checked, on_coded, summary)
    return await smoke_plan(smoke, coded, repair, summary, concurrency, recode, replan)


async def _promote_sibling(
    coded: AnalysisPlan,
    step_id: str,
    default_id: str,
    error: str | None,
    attempts_by_option: dict[tuple[str, str], int],
    models_by_option: dict[tuple[str, str], list[str]],
    on_coded: OnCoded | None,
) -> None:
    target = coded.step(step_id)
    sibling = next((o for o in target.options if o.code is not None), None)
    if sibling is None:
        raise LLMError(f"default option {step_id}.{default_id} failed coding: {error}")
    sibling.is_default = True
    if on_coded is not None:
        note = f"promoted to default because {default_id} failed coding: {error}"
        attempts = attempts_by_option.get((step_id, sibling.id), 1)
        await on_coded(
            step_id,
            sibling.id,
            True,
            attempts,
            note,
            models_by_option.get((step_id, sibling.id), []),
        )


async def repair_option(
    llm: LLMClient, plan: AnalysisPlan, step: Step, option: Option, error: str
) -> Option:
    code = await _request_code(llm, plan, step, option, error)
    violations = check_code(code, step.kind, option_intent(option))
    if violations:
        raise LLMError(
            f"repaired code for {step.id}.{option.id} violates the guard: " + "; ".join(violations)
        )
    return option.model_copy(update={"code": code})
