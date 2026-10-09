"""Options a re-plan proposes are judged like the plan's own before they are coded.

The data of r_20261009T021141_d6ab2f had no smoking column. Every option of the step that cleaned
the smoking flag failed, the re-plan proposed proxy_smoking = (age > 50) & (bmi > 25) as the new
default, and the run reported SMOKING CAUSES LUNG DISEASE (p = 0.001) on that invented exposure:
re-planned options went to coding without Model Armor or the judge. They now pass both, as
alternatives of the step they replace. A scripted run asks the judge only for the verdicts its
fixtures hold, so recordings made before this replay unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from borges.analysis.judge import judge_key
from borges.analysis.models import AnalysisPlan, CodingSummary, Option, Step
from borges.analysis.smoke_types import Admit
from borges.llm.client import LLMClient
from borges.llm.gather import gather_cancelling
from borges.memory.run_memory import RunMemory
from borges.runs.emitter import RunEmitter
from borges.runs.judged_ledger import JudgedLedger
from borges.runs.plan_judging import Screen, judge_alternative

if TYPE_CHECKING:
    from borges.runs.pipeline import Pipeline


def replan_admit(
    llm: LLMClient,
    plan: AnalysisPlan,
    emitter: RunEmitter,
    summary: CodingSummary,
    ledger: JudgedLedger,
    memory: RunMemory | None,
    screen: Screen | None,
) -> Admit:
    holds = getattr(llm, "holds", None)

    async def verdict(step: Step, option: Option) -> Option | None:
        if holds is not None and not holds(judge_key(step, option, "planner")):
            return option
        judged, _ = await judge_alternative(llm, plan, emitter, step, option, ledger, memory)
        return judged

    async def admit(step: Step, options: list[Option]) -> list[Option]:
        screened = await screen(step.id, options) if screen is not None else options
        judged = await gather_cancelling(verdict(step, option) for option in screened)
        kept = [option for option in judged if option is not None]
        summary.options_dropped_by_judge += len(screened) - len(kept)
        return kept

    return admit


def admit_replans(pipeline: Pipeline, plan: AnalysisPlan) -> Admit:
    screen = pipeline.armor_stage.planner_options
    return replan_admit(
        pipeline.llm,
        plan,
        pipeline.emitter,
        pipeline.coding,
        pipeline.judged,
        pipeline.memory,
        screen,
    )
