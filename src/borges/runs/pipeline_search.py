from __future__ import annotations

from typing import TYPE_CHECKING

from borges.analysis.models import AnalysisPlan
from borges.garden.executor import GardenExecutor
from borges.garden.search import minimal_flip, single_flip_choices
from borges.runs.pipeline_stages import (
    run_adversary,
    run_combinations,
    run_uniform_sample,
    tolerate_budget,
)
from borges.runs.runner import UniverseRunner
from borges.runtime.alias_backend import AliasBackend
from borges.runtime.restore_search import restore_search

if TYPE_CHECKING:
    from borges.runs.pipeline import Pipeline


async def search_garden(pipeline: Pipeline, plan: AnalysisPlan) -> None:
    backend = AliasBackend(pipeline.backend) if pipeline.restored else pipeline.backend
    executor = GardenExecutor(
        backend,
        plan,
        pipeline.resolved.data,
        pipeline.emitter.emit,
        pipeline.settings.borges_concurrency,
        step_timeout_s=pipeline.settings.borges_step_timeout_s,
    )
    pipeline.executor = executor
    if pipeline.restored and isinstance(backend, AliasBackend):
        await restore_search(executor, backend, plan, pipeline.restored)
    else:
        await executor.setup()
    runner = UniverseRunner(
        pipeline.llm,
        plan,
        executor,
        pipeline.garden,
        pipeline.emitter,
        pipeline.resolved.max_universes,
        context=pipeline.context,
        restored=pipeline.restored,
        root_id=getattr(getattr(executor, "root", None), "id", None),
    )
    async with pipeline.stage("baseline"):
        baseline = await runner.run(plan.default_choices(), "baseline")
        if baseline.status != "done":
            raise RuntimeError(f"the baseline analysis failed: {baseline.error}")
    async with pipeline.stage("single_flips"):
        singles = single_flip_choices(plan)
        if len(singles) > runner.remaining:
            pipeline.search.budget_exhausted = True
            pipeline.caveats.append(
                "The universe budget ran out before every single-decision flip was tried."
            )
        pipeline.search.levels_explored = 1
        await tolerate_budget(
            pipeline, runner.run_many(singles, "single"), "The single-decision flips stopped early"
        )
    if runner.remaining > 0:
        await run_adversary(pipeline, plan, runner, baseline)
    else:
        pipeline.search.budget_exhausted = True
        pipeline.caveats.append("The universe budget ran out before the adversary stage ran.")
    pipeline.flip = minimal_flip(plan, pipeline.garden)
    if pipeline.flip is None and runner.remaining > 0:
        await tolerate_budget(
            pipeline,
            run_combinations(pipeline, plan, runner),
            "The combination flips stopped early",
        )
    elif pipeline.flip is None and len(plan.decision_steps) > 1:
        pipeline.search.budget_exhausted = True
    await run_uniform_sample(pipeline, plan, runner)
    pipeline.search.universes_used = len(pipeline.garden.universes)
