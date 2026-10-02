from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Universe
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
            )
        except Exception as exc:
            pipeline.caveats.append(f"The adversary stage failed and was skipped: {exc}")


async def run_combinations(pipeline: Pipeline, plan: AnalysisPlan, runner: UniverseRunner) -> None:
    async with pipeline.stage("combination_flips"):
        for size in range(2, len(plan.decision_steps) + 1):
            if pipeline.flip is not None:
                break
            if runner.remaining <= 0:
                pipeline.search.budget_exhausted = True
                break
            limit = min(MAX_COMBINATIONS_PER_LEVEL, runner.remaining)
            choices = combination_flip_choices(plan, pipeline.garden, size, limit)
            if not choices:
                break
            pipeline.search.levels_explored = size
            await pipeline.emitter.stage("combination_flips", "started", f"{size} changes")
            await runner.run_many(choices, "combination")
            pipeline.flip = minimal_flip(plan, pipeline.garden)
