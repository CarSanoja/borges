from __future__ import annotations

from typing import TYPE_CHECKING

from borges.analysis.models import AnalysisPlan
from borges.analysis.narrator import narrate
from borges.garden.models import Report
from borges.garden.verify import verify_flip

if TYPE_CHECKING:
    from borges.runs.pipeline import Pipeline


async def verify_stage(pipeline: Pipeline, plan: AnalysisPlan) -> None:
    if pipeline.flip is None:
        return
    emitter = pipeline.emitter
    await emitter.emit("flip.found", {"flip": pipeline.flip.model_dump(mode="json")})
    async with pipeline.stage("verifying"):
        try:
            pipeline.flip = await verify_flip(
                pipeline.backend,
                plan,
                pipeline.resolved.data,
                pipeline.flip,
                pipeline.garden,
                step_timeout_s=pipeline.settings.borges_step_timeout_s,
            )
        except Exception as exc:
            pipeline.caveats.append(
                f"The minimal flip could not be re-run in a fresh sandbox ({exc}); "
                "it is unverified."
            )
        if pipeline.flip.reproduced is False:
            pipeline.caveats.append(
                "The minimal flip did not reproduce in a fresh sandbox; treat it as unconfirmed."
            )
        await emitter.emit("flip.verified", {"flip": pipeline.flip.model_dump(mode="json")})


async def narrate_stage(pipeline: Pipeline, plan: AnalysisPlan, report: Report) -> None:
    async with pipeline.stage("narrating"):
        try:
            narrative, caveats = await narrate(pipeline.llm, plan, report)
            report.narrative = narrative
            report.caveats = [*report.caveats, *caveats]
        except Exception as exc:
            report.caveats = [*report.caveats, f"Narrative unavailable: {exc}"]
        report.agents = pipeline.agents
        await pipeline.emitter.emit("report.ready", {"report": report.model_dump(mode="json")})
