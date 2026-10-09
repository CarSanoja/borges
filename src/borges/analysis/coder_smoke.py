from __future__ import annotations

import asyncio
import io
from functools import partial

import pyarrow.parquet as pq

from borges.analysis import harness
from borges.analysis.models import AnalysisPlan, CodingSummary, Option, Step
from borges.analysis.smoke_collision import resolve_outputs
from borges.analysis.smoke_core import execute, sample_rows, smoke_option
from borges.analysis.smoke_larger import LARGE_MAX_ROWS, LargerSample, smoke_rows
from borges.analysis.smoke_model_probe import probe_model
from borges.analysis.smoke_orientation import apply_orientation, effective_default
from borges.analysis.smoke_origin import cut_names
from borges.analysis.smoke_recode import recode_failed_default
from borges.analysis.smoke_replan import has_survivor
from borges.analysis.smoke_review import review_step
from borges.analysis.smoke_settle import Tools, settle
from borges.analysis.smoke_types import Outcome, Recode, Repair, Replan, Rewrite, SmokeConfig
from borges.analysis.smoke_upstream import _short
from borges.analysis.smoke_upstream_probe import probe_upstream
from borges.analysis.smoke_upstream_repair import Mark, mark, repair_upstream_default, restart
from borges.analysis.smoke_upstream_replan import replan_upstream
from borges.llm.client import LLMError
from borges.sandbox.backend import Checkpoint
from borges.telemetry.scopes import option_span

FAILED_NOTE = (
    "The option '{label}' of the step '{title}' failed its smoke run and is not in the analysis "
    "({error})."
)

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
            with option_span("option.smoke", step.id, option.id) as span:
                outcome = await smoke_option(config, repair, parent, step, option)
                span.set_attribute("borges.option.status", outcome.status)
                span.set_attribute("borges.option.attempts", outcome.attempts)
        if config.on_smoke is not None:
            await config.on_smoke(
                step.id,
                option.id,
                outcome.status,
                outcome.attempts,
                outcome.error,
                outcome.models,
                *smoke_rows(outcome),
            )
        return outcome

    return list(await asyncio.gather(*(work(o) for o in step.options if o.code is not None)))


def _record(summary: CodingSummary | None, outcomes: list[Outcome]) -> None:
    if summary is None:
        return
    summary.smoke_tested += len(outcomes)
    summary.repaired_after_smoke += sum(1 for o in outcomes if o.status == "repaired")
    summary.failed += sum(1 for o in outcomes if o.status == "failed")


def _all_failed_message(step: Step, default_id: str, outcomes: list[Outcome]) -> str:
    tried = ", ".join(o.option.id for o in outcomes) or default_id
    failed = next((o for o in outcomes if o.option.id == default_id), None)
    last = next((o.error for o in reversed(outcomes) if o.error), None)
    reason = (failed.error if failed and failed.error else last) or "not coded"
    return (
        f"step {step.id}: no option passed its smoke run (default {default_id} failed "
        f"after repairs and a fresh re-code); options tried: {tried}; last error: {reason}"
    )


def _apply(step: Step, outcomes: list[Outcome]) -> tuple[Checkpoint, Option | None, str]:
    default_id = step.default.id
    survivors = {o.option.id: o for o in outcomes if o.status != "failed"}
    step.options = [survivors[o.id].option for o in step.options if o.id in survivors]
    if default_id not in survivors:
        failed = next((o for o in outcomes if o.option.id == default_id), None)
        if not step.options:
            raise LLMError(_all_failed_message(step, default_id, outcomes))
        step.options[0].is_default = True
        reason = failed.error if failed and failed.error else "not coded"
        return survivors[step.default.id].checkpoint, step.options[0], f"{default_id}: {reason}"
    return survivors[step.default.id].checkpoint, None, ""


async def _smoke_round(
    config: SmokeConfig,
    repair: Repair,
    recode: Recode | None,
    parent: Checkpoint,
    step: Step,
    semaphore: asyncio.Semaphore,
    summary: CodingSummary | None,
) -> list[Outcome]:
    outcomes = await _smoke_step(config, repair, parent, step, semaphore)
    _record(summary, outcomes)
    outcomes = await recode_failed_default(config, repair, recode, parent, step, outcomes)
    outcomes = await apply_orientation(config, repair, parent, step, outcomes, summary)
    outcomes = await review_step(config, repair, parent, step, outcomes, summary)
    return await resolve_outputs(config, repair, parent, step, outcomes, summary)


async def _runs_as_written(
    config: SmokeConfig, repair: Repair, step: Step, parent: Checkpoint
) -> bool:
    for option in step.options:
        if option.code is None:
            continue
        outcome = await smoke_option(config, repair, parent, step, option, budget=0)
        if outcome.status != "failed":
            return True
    return False


async def _rerun(
    config: SmokeConfig,
    repair: Repair,
    recode: Recode | None,
    step: Step,
    semaphore: asyncio.Semaphore,
    summary: CodingSummary | None,
    parent: Checkpoint,
) -> list[Outcome]:
    return await _smoke_round(config, repair, recode, parent, step, semaphore, summary)


async def smoke_plan(
    config: SmokeConfig,
    plan: AnalysisPlan,
    repair: Repair,
    summary: CodingSummary | None = None,
    concurrency: int = 6,
    recode: Recode | None = None,
    replan: Replan | None = None,
    rewrite: Rewrite | None = None,
) -> AnalysisPlan:
    smoked = plan.model_copy(deep=True)
    config.rewrite = rewrite
    config.metric = plan.decision_rule.metric
    config.state.cut = cut_names(smoked.steps)
    sample = sample_rows(config.data)
    parent = await config.backend.root({harness.DATA_FILE: sample})
    sample_n = pq.read_metadata(io.BytesIO(sample)).num_rows
    config.larger = LargerSample(config, smoked.steps, sample_n, execute, LARGE_MAX_ROWS)
    semaphore = asyncio.Semaphore(concurrency)
    marks: dict[str, Mark] = {}
    repaired_upstream = False
    index = 0
    while index < len(smoked.steps):
        step = smoked.steps[index]
        marks[step.id] = mark(config, summary, step)
        again = partial(_smoke_round, config, repair, recode, parent, step, semaphore, summary)
        outcomes = await again()
        if not has_survivor(outcomes) and step.kind == "model" and index > 0:
            earlier = smoked.steps[index - 1]
            upstream = await replan_upstream(
                config,
                replan,
                earlier,
                step,
                outcomes,
                partial(
                    _smoke_round,
                    config,
                    repair,
                    recode,
                    config.state.parents[earlier.id],
                    earlier,
                    semaphore,
                    summary,
                ),
                partial(_rerun, config, repair, recode, step, semaphore, summary),
            )
            if upstream is not None:
                parent, outcomes = upstream
        if not has_survivor(outcomes) and step.kind == "model" and not repaired_upstream:
            fixed = await repair_upstream_default(config, repair, smoked.steps, index, outcomes)
            if fixed is not None:
                repaired_upstream = True
                restart(config, summary, marks, smoked.steps, (fixed[0], index), fixed[1])
                index = fixed[0]
                parent = config.state.parents[smoked.steps[index].id]
                continue
        if not has_survivor(outcomes):
            tools = Tools(
                partial(_rerun, config, repair, recode, step, semaphore, summary),
                partial(_runs_as_written, config, repair, step),
            )
            parent, outcomes = await settle(
                config, replan, smoked.steps, index, parent, outcomes, tools
            )
        config.state.parents[step.id] = parent
        live_default = effective_default(step, outcomes)
        if live_default is not None:
            config.state.defaults[step.id] = live_default
        replaced = step.default
        parent, promoted, cause = _apply(step, outcomes)
        config.state.outcomes[step.id] = [o for o in outcomes if o.status != "failed"]
        config.state.notes.extend(
            FAILED_NOTE.format(label=o.option.label, title=step.title, error=_short(o.error or ""))
            for o in outcomes
            if o.status == "failed" and o.option.id != replaced.id
        )
        if promoted is not None:
            config.state.notes.append(
                f"The default option {step.id}.{replaced.id} ({replaced.label}) failed its smoke "
                f"run and was replaced by {promoted.id} ({promoted.label}): {cause}."
            )
        if promoted is not None and config.on_smoke is not None:
            chosen = next(o for o in outcomes if o.option.id == promoted.id)
            note = f"promoted to default because {cause} failed its smoke run"
            await config.on_smoke(
                step.id, promoted.id, chosen.status, chosen.attempts, note, chosen.models
            )
        if step.kind == "model" and index > 0:
            await probe_upstream(config, repair, smoked.steps[index - 1], step, summary)
            await probe_model(config, repair, smoked.steps, index, summary)
        index += 1
    return smoked
