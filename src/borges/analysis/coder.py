from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from borges.analysis.code_guard import check_code
from borges.analysis.models import AnalysisPlan, Option, Step
from borges.analysis.prompts.coder import build_messages
from borges.analysis.schemas import CoderOutput
from borges.llm.client import LLMClient, LLMError, Role

OnCoded = Callable[[str, str, bool, int, str | None], Awaitable[None]]


async def _request_code(
    llm: LLMClient, plan: AnalysisPlan, step: Step, option: Option, error: str | None = None
) -> str:
    key = f"coder:{step.id}.{option.id}" + (":repair" if error is not None else "")
    response = await llm.complete(
        Role.CODER,
        build_messages(plan, step, option, error),
        key=key,
        schema=CoderOutput,
        max_tokens=1500,
    )
    return CoderOutput.model_validate(response.parsed).code


async def generate_checked(
    llm: LLMClient, plan: AnalysisPlan, step: Step, option: Option
) -> tuple[str | None, int, str | None]:
    code = await _request_code(llm, plan, step, option)
    violations = check_code(code, step.kind)
    if not violations:
        return code, 1, None
    error = "\n".join(violations)
    draft = option.model_copy(update={"code": code})
    code = await _request_code(llm, plan, step, draft, error)
    violations = check_code(code, step.kind)
    if not violations:
        return code, 2, None
    return None, 2, "\n".join(violations)


async def code_option(llm: LLMClient, plan: AnalysisPlan, step: Step, option: Option) -> str:
    """Code one option, passing the code guard with one repair attempt, or raise LLMError."""
    code, _, error = await generate_checked(llm, plan, step, option)
    if code is None:
        raise LLMError(f"code for {step.id}.{option.id} violates the guard: {error}")
    return code


async def code_plan(
    llm: LLMClient, plan: AnalysisPlan, on_coded: OnCoded | None = None, concurrency: int = 6
) -> AnalysisPlan:
    semaphore = asyncio.Semaphore(concurrency)

    async def work(step: Step, option: Option) -> tuple[str | None, str | None]:
        async with semaphore:
            try:
                code, attempts, error = await generate_checked(llm, plan, step, option)
            except LLMError as exc:
                code, attempts, error = None, 1, str(exc)
        if on_coded is not None:
            await on_coded(step.id, option.id, code is not None, attempts, error)
        return code, error

    pending = [(s, o) for s in plan.steps for o in s.options if o.code is None]
    results = await asyncio.gather(*(work(s, o) for s, o in pending))

    coded = plan.model_copy(deep=True)
    for (step, option), (code, error) in zip(pending, results, strict=True):
        target = coded.step(step.id)
        if code is not None:
            target.option(option.id).code = code
        elif option.is_default:
            raise LLMError(f"default option {step.id}.{option.id} failed coding: {error}")
        else:
            target.options = [o for o in target.options if o.id != option.id]
    return coded


async def repair_option(
    llm: LLMClient, plan: AnalysisPlan, step: Step, option: Option, error: str
) -> Option:
    code = await _request_code(llm, plan, step, option, error)
    violations = check_code(code, step.kind)
    if violations:
        raise LLMError(
            f"repaired code for {step.id}.{option.id} violates the guard: " + "; ".join(violations)
        )
    return option.model_copy(update={"code": code})
