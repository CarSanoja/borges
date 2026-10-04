from __future__ import annotations

from collections.abc import Awaitable, Callable

from borges.analysis.model_spec.request import template_family
from borges.analysis.models import AnalysisPlan, CodingSummary, Option, Step
from borges.analysis.smoke_types import Outcome, Replan, Replanned
from borges.analysis.step_replan import propose_options
from borges.llm.client import LLMClient, LLMError
from borges.llm.gather import gather_cancelling
from borges.telemetry.scopes import option_span

Generate = Callable[
    [LLMClient, AnalysisPlan, Step, Option, list[str] | None],
    Awaitable[tuple[str | None, int, str | None]],
]
OnCoded = Callable[[str, str, bool, int, str | None, list[str]], Awaitable[None]]


def make_replan(
    llm: LLMClient,
    plan: AnalysisPlan,
    generate: Generate,
    on_coded: OnCoded | None,
    summary: CodingSummary | None,
) -> Replan:
    async def replan(step: Step, outcomes: list[Outcome]) -> Replanned | None:
        proposed = await propose_options(llm, plan, step, outcomes)
        if proposed is None:
            return None
        candidate = step.model_copy(update={"options": proposed})

        async def work(option: Option) -> tuple[str | None, int, str | None]:
            models: list[str] = []
            with option_span("option.code", step.id, option.id) as span:
                try:
                    code, attempts, error = await generate(llm, plan, candidate, option, models)
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

        results = await gather_cancelling(work(o) for o in proposed)
        coded: list[Option] = []
        errors: dict[str, str] = {}
        for option, (code, _, error) in zip(proposed, results, strict=True):
            if code is None:
                errors[option.id] = error or "not coded"
                continue
            coded.append(option.model_copy(update={"code": code}))
        if summary is not None:
            summary.options += len(proposed)
            summary.failed += len(errors)
        if coded and not any(o.is_default for o in coded):
            coded[0].is_default = True
        return Replanned(coded, errors)

    return replan
