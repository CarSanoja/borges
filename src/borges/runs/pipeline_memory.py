from __future__ import annotations

from typing import TYPE_CHECKING

from borges.analysis.models import AnalysisPlan, DatasetProfile
from borges.runs.events import MemoryUsedData
from borges.runs.pipeline_callbacks import OnCoded

if TYPE_CHECKING:
    from borges.runs.pipeline import Pipeline


def recall_profile(pipeline: Pipeline, profile: DatasetProfile) -> DatasetProfile:
    if pipeline.memory is None:
        return profile
    return pipeline.memory.attach(profile)


async def prefill_code(pipeline: Pipeline, plan: AnalysisPlan, on_coded: OnCoded) -> None:
    memory = pipeline.memory
    if memory is None:
        return
    for step in plan.steps:
        for option in step.options:
            if option.code is not None:
                continue
            code = memory.recall_code(plan, step, option)
            if code is None:
                continue
            option.code = code
            pipeline.coding.options += 1
            await on_coded(step.id, option.id, True, 1, None, [])


async def finish_memory(pipeline: Pipeline, plan: AnalysisPlan | None, announce: bool) -> None:
    memory = pipeline.memory
    if memory is None or memory.finished:
        return
    if plan is not None:
        memory.remember_codes(plan, pipeline.garden)
    memory.finish()
    usage = memory.session.usage()
    if announce and (usage["reused"] or usage["stored"]):
        data = MemoryUsedData.model_validate(usage)
        await pipeline.emitter.emit("memory.used", data.model_dump(mode="json"))
