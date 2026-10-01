from __future__ import annotations

import asyncio

from borges.analysis.adversary import propose_options
from borges.analysis.coder import code_option
from borges.analysis.judge import judge_option
from borges.analysis.models import AnalysisPlan, Option, Proposal
from borges.garden.models import Universe
from borges.llm.client import BudgetExceeded, LLMClient
from borges.runs.emitter import RunEmitter
from borges.runs.events import OptionCodedData, OptionJudgedData
from borges.runs.runner import UniverseRunner, publish_plan


async def _judge_and_code(
    llm: LLMClient, plan: AnalysisPlan, emitter: RunEmitter, proposal: Proposal
) -> tuple[str, Option] | None:
    step = plan.step(proposal.step_id)
    option = proposal.option
    judgement = await judge_option(llm, plan, step, option)
    judged = OptionJudgedData(
        step_id=step.id,
        option_id=option.id,
        defensibility=judgement.defensibility,
        accepted=judgement.accepted,
        reason=judgement.reason,
    )
    await emitter.emit("option.judged", judged.model_dump(mode="json"))
    if not judgement.accepted:
        return None
    option = option.model_copy(
        update={
            "defensibility": judgement.defensibility,
            "source": judgement.source or option.source,
        }
    )
    try:
        code = await code_option(llm, plan, step, option)
    except BudgetExceeded:
        raise
    except Exception as exc:
        failed = OptionCodedData(
            step_id=step.id, option_id=option.id, ok=False, attempts=1, error=str(exc)
        )
        await emitter.emit("option.coded", failed.model_dump(mode="json"))
        return None
    return step.id, option.model_copy(update={"code": code})


async def run_adversary_round(
    llm: LLMClient,
    plan: AnalysisPlan,
    runner: UniverseRunner,
    emitter: RunEmitter,
    baseline: Universe,
) -> list[Universe]:
    """Propose options from the real baseline state, judge them, then flip each accepted one."""
    proposals = [
        p
        for p in await propose_options(llm, plan, baseline)
        if any(s.id == p.step_id for s in plan.steps)
    ]
    for proposal in proposals:
        payload = {"step_id": proposal.step_id, "option": proposal.option.model_dump(mode="json")}
        await emitter.emit("option.proposed", payload)
    outcomes = await asyncio.gather(*(_judge_and_code(llm, plan, emitter, p) for p in proposals))
    accepted = [o for o in outcomes if o is not None]
    for step_id, option in accepted:
        plan.step(step_id).options.append(option)
    if proposals:
        await publish_plan(emitter, plan)
    if not accepted:
        return []
    defaults = plan.default_choices()
    choices = [{**defaults, step_id: option.id} for step_id, option in accepted]
    return await runner.run_many(choices, "adversary")
