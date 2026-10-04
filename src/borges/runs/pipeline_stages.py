from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING

from borges.analysis.models import AnalysisPlan
from borges.garden.duplicates import excluded_options
from borges.garden.models import Universe
from borges.garden.sampling import (
    MIN_SAMPLE,
    SAMPLE_DRAWS,
    affordable_prefix,
    draw_grid,
    sampled_ids,
)
from borges.garden.search import combination_flip_choices, minimal_flip
from borges.llm.client import BudgetExceeded
from borges.runs.adversary_round import run_adversary_round
from borges.runs.runner import UniverseRunner

if TYPE_CHECKING:
    from borges.runs.pipeline import Pipeline

MAX_COMBINATIONS_PER_LEVEL = 10


async def tolerate_budget(pipeline: Pipeline, work: Awaitable[object], label: str) -> None:
    try:
        await work
    except BudgetExceeded as exc:
        pipeline.search.budget_exhausted = True
        pipeline.caveats.append(f"{label} because the spend or run cap was reached: {exc}")


async def run_adversary(
    pipeline: Pipeline, plan: AnalysisPlan, runner: UniverseRunner, baseline: Universe
) -> None:
    async with pipeline.stage("adversary"):
        seen = len(pipeline.smoke.state.notes) if pipeline.smoke is not None else 0
        try:
            await run_adversary_round(
                pipeline.llm,
                plan,
                runner,
                pipeline.emitter,
                baseline,
                pipeline.smoke,
                pipeline.judged,
                pipeline.armor_stage,
                pipeline.memory,
            )
        except Exception as exc:
            pipeline.caveats.append(f"The adversary stage failed and was skipped: {exc}")
        if pipeline.smoke is not None:
            pipeline.caveats.extend(pipeline.smoke.state.notes[seen:])


def sample_reserve(runner: UniverseRunner) -> int:
    return min(SAMPLE_DRAWS, runner.remaining // 2)


async def run_combinations(pipeline: Pipeline, plan: AnalysisPlan, runner: UniverseRunner) -> None:
    async with pipeline.stage("combination_flips"):
        reserve = sample_reserve(runner)
        for size in range(2, len(plan.decision_steps) + 1):
            if pipeline.flip is not None:
                break
            if runner.remaining - reserve <= 0:
                pipeline.search.budget_exhausted = True
                break
            limit = min(MAX_COMBINATIONS_PER_LEVEL, runner.remaining - reserve)
            choices = combination_flip_choices(plan, pipeline.garden, size, limit)
            if not choices:
                break
            pipeline.search.levels_explored = size
            await pipeline.emitter.stage("combination_flips", "started", f"{size} changes")
            await runner.run_many(choices, "combination")
            pipeline.flip = minimal_flip(plan, pipeline.garden)


async def run_uniform_sample(
    pipeline: Pipeline, plan: AnalysisPlan, runner: UniverseRunner
) -> None:
    garden = pipeline.garden
    noops = excluded_options(plan, garden)
    draws = draw_grid(plan, noops)
    kept, new = affordable_prefix(draws, garden, runner.remaining)
    if len(kept) < MIN_SAMPLE:
        return
    await tolerate_budget(
        pipeline, runner.run_many(new, "combination"), "The uniform grid sample stopped early"
    )
    garden.sample_ids = sampled_ids(garden, kept)
    pipeline.search.sample_draws = len(kept)
