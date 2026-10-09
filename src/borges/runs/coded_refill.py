"""Alternatives the coder lost, proposed again.

In the fertility_social held-out attempt r_20261009T071205_467cac (9 October 2026) the judge left
three steps with alternatives; then one alternative's code failed its smoke run and another did
not do what its spec said, so the garden searched a plan with a single branching step and could
not find the flip the published grid holds. A step the judge collapses is refilled; one the coder
collapses now is too, and the new alternatives are judged, coded and smoke-run like the
adversary's.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from borges.analysis.models import AnalysisPlan, Proposal, Step
from borges.analysis.plan_refill import collapsed_steps, propose_refill
from borges.llm.gather import gather_cancelling
from borges.runs.adversary_round import judge_and_code
from borges.runs.runner import publish_plan

if TYPE_CHECKING:
    from borges.runs.pipeline import Pipeline

LOST = "its code could not be made to run on the data, or did not do what its spec says"


async def _refill(pipeline: Pipeline, planned: AnalysisPlan, plan: AnalysisPlan, step: Step) -> int:
    kept_ids = {o.id for o in step.options}
    lost = [(o, LOST) for o in planned.step(step.id).options if o.id not in kept_ids]
    options = await propose_refill(pipeline.llm, plan, step, lost, failed=True)
    options = await pipeline.armor_stage.planner_options(step.id, options)
    coded = await gather_cancelling(
        judge_and_code(
            pipeline.llm,
            plan,
            pipeline.emitter,
            Proposal(step_id=step.id, option=option),
            pipeline.smoke,
            pipeline.memory,
            origin="planner",
        )
        for option in options
    )
    added = [option for _, option in filter(None, coded)]
    step.options.extend(added)
    return len(added)


async def refill_coded(pipeline: Pipeline, planned: AnalysisPlan, plan: AnalysisPlan) -> None:
    """Refill the steps coding left with one option when too few steps still branch."""
    before = {step.id: len(step.options) for step in planned.steps}
    steps = collapsed_steps(plan, before)
    if not steps:
        return
    added = await gather_cancelling(_refill(pipeline, planned, plan, step) for step in steps)
    pipeline.coding.options_added_after_judge += sum(added)
    if sum(added):
        await publish_plan(pipeline.emitter, plan)
