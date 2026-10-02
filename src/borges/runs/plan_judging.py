from __future__ import annotations

from borges.analysis.judge import judge_option
from borges.analysis.models import AnalysisPlan, CodingSummary, Option, Step
from borges.llm.client import BudgetExceeded, LLMClient
from borges.llm.gather import gather_cancelling
from borges.runs.emitter import RunEmitter
from borges.runs.events import OptionJudgedData
from borges.runs.runner import publish_plan


async def _judge_alternative(
    llm: LLMClient, plan: AnalysisPlan, emitter: RunEmitter, step: Step, option: Option
) -> Option | None:
    try:
        judgement = await judge_option(llm, plan, step, option, "planner")
    except BudgetExceeded:
        raise
    except Exception as exc:
        data = OptionJudgedData(
            step_id=step.id,
            option_id=option.id,
            defensibility=0.0,
            accepted=False,
            reason=f"judge failed: {exc}",
            origin="planner",
        )
        await emitter.emit("option.judged", data.model_dump(mode="json"))
        return None
    data = OptionJudgedData(
        step_id=step.id,
        option_id=option.id,
        defensibility=judgement.defensibility,
        accepted=judgement.accepted,
        reason=judgement.reason,
        origin="planner",
    )
    await emitter.emit("option.judged", data.model_dump(mode="json"))
    if not judgement.accepted:
        return None
    return option.model_copy(
        update={
            "defensibility": judgement.defensibility,
            "source": option.source or judgement.source,
        }
    )


async def judge_plan_options(
    llm: LLMClient, plan: AnalysisPlan, emitter: RunEmitter, summary: CodingSummary
) -> None:
    """Judge every non-default planner option; drop the rejected ones before any coding."""
    targets = [(s, o) for s in plan.steps for o in s.options if not o.is_default]
    if not targets:
        return
    outcomes = await gather_cancelling(
        _judge_alternative(llm, plan, emitter, step, option) for step, option in targets
    )
    replaced = {
        (step.id, option.id): judged
        for (step, option), judged in zip(targets, outcomes, strict=True)
    }
    for step in plan.steps:
        step.options = [
            replaced.get((step.id, o.id), o)
            for o in step.options
            if replaced.get((step.id, o.id), o) is not None
        ]
    summary.options_dropped_by_judge += sum(1 for o in outcomes if o is None)
    await publish_plan(emitter, plan)
