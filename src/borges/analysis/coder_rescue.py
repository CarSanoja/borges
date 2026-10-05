from __future__ import annotations

from collections.abc import Callable

from borges.analysis.coder_replan import Generate, OnCoded, make_replan
from borges.analysis.models import AnalysisPlan, CodingSummary, Option, Step
from borges.analysis.smoke_types import OnReplan, Outcome
from borges.llm.client import LLMClient, LLMError


async def replan_uncoded_step(
    llm: LLMClient,
    coded: AnalysisPlan,
    step: Step,
    errors: dict[str, tuple[int, str | None]],
    generate: Generate,
    on_coded: OnCoded | None,
    summary: CodingSummary | None,
    on_replan: OnReplan | None,
    refused: Callable[[str, Option], bool] | None = None,
) -> bool:
    outcomes = [
        Outcome(
            option=option,
            status="failed",
            attempts=errors.get(option.id, (1, None))[0],
            error=errors.get(option.id, (1, None))[1],
            checkpoint=None,
            models=[],
        )
        for option in step.options
    ]
    replan = make_replan(llm, coded, generate, on_coded, summary, refused)
    replanned = await replan(step, outcomes)
    if replanned is None or not replanned.options:
        return False
    coded.step(step.id).options = replanned.options
    if on_replan is not None:
        await on_replan(step.id, [o.id for o in step.options], [o.id for o in replanned.options])
    return True


async def promote_sibling(
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
