from __future__ import annotations

import asyncio

from borges.analysis import harness
from borges.analysis.models import AnalysisPlan, CodingSummary, Option, Step
from borges.analysis.smoke_core import sample_rows, smoke_option
from borges.analysis.smoke_orientation import apply_orientation, effective_default
from borges.analysis.smoke_review import review_step
from borges.analysis.smoke_types import Outcome, Repair, SmokeConfig
from borges.llm.client import LLMError
from borges.sandbox.backend import Checkpoint

__all__ = ["SmokeConfig", "sample_rows", "smoke_plan"]


async def _smoke_step(
    config: SmokeConfig,
    repair: Repair,
    parent: Checkpoint,
    step: Step,
    semaphore: asyncio.Semaphore,
) -> list[Outcome]:
    async def work(option: Option) -> Outcome:
        async with semaphore:
            outcome = await smoke_option(config, repair, parent, step, option)
        if config.on_smoke is not None:
            await config.on_smoke(
                step.id, option.id, outcome.status, outcome.attempts, outcome.error, outcome.models
            )
        return outcome

    return list(await asyncio.gather(*(work(o) for o in step.options if o.code is not None)))


def _record(summary: CodingSummary | None, outcomes: list[Outcome]) -> None:
    if summary is None:
        return
    summary.smoke_tested += len(outcomes)
    summary.repaired_after_smoke += sum(1 for o in outcomes if o.status == "repaired")
    summary.failed += sum(1 for o in outcomes if o.status == "failed")


def _apply(step: Step, outcomes: list[Outcome]) -> tuple[Checkpoint, Option | None, str]:
    default_id = step.default.id
    survivors = {o.option.id: o for o in outcomes if o.status != "failed"}
    step.options = [survivors[o.id].option for o in step.options if o.id in survivors]
    if default_id not in survivors:
        failed = next((o for o in outcomes if o.option.id == default_id), None)
        if not step.options:
            reason = failed.error if failed else "not coded"
            raise LLMError(f"default option {step.id}.{default_id} failed its smoke run: {reason}")
        step.options[0].is_default = True
        reason = failed.error if failed and failed.error else "not coded"
        return survivors[step.default.id].checkpoint, step.options[0], f"{default_id}: {reason}"
    return survivors[step.default.id].checkpoint, None, ""


async def smoke_plan(
    config: SmokeConfig,
    plan: AnalysisPlan,
    repair: Repair,
    summary: CodingSummary | None = None,
    concurrency: int = 6,
) -> AnalysisPlan:
    smoked = plan.model_copy(deep=True)
    parent = await config.backend.root({harness.DATA_FILE: sample_rows(config.data)})
    semaphore = asyncio.Semaphore(concurrency)
    for step in smoked.steps:
        outcomes = await _smoke_step(config, repair, parent, step, semaphore)
        _record(summary, outcomes)
        outcomes = await apply_orientation(config, repair, parent, step, outcomes, summary)
        outcomes = await review_step(config, repair, parent, step, outcomes, summary)
        config.state.parents[step.id] = parent
        live_default = effective_default(step, outcomes)
        if live_default is not None:
            config.state.defaults[step.id] = live_default
        parent, promoted, cause = _apply(step, outcomes)
        if promoted is not None and config.on_smoke is not None:
            chosen = next(o for o in outcomes if o.option.id == promoted.id)
            note = f"promoted to default because {cause} failed its smoke run"
            await config.on_smoke(
                step.id, promoted.id, chosen.status, chosen.attempts, note, chosen.models
            )
    return smoked
