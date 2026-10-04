from __future__ import annotations

from collections.abc import Awaitable, Callable

from borges.analysis.judge import judge_option
from borges.analysis.models import AnalysisPlan, CodingSummary, Option, Step
from borges.analysis.plan_refill import Rejected, collapsed_steps, propose_refill
from borges.llm.client import BudgetExceeded, LLMClient
from borges.llm.gather import gather_cancelling
from borges.memory.run_memory import RunMemory
from borges.runs.emitter import RunEmitter
from borges.runs.events import OptionJudgedData
from borges.runs.judged_ledger import JudgedLedger
from borges.runs.runner import publish_plan

Screen = Callable[[str, list[Option]], Awaitable[list[Option]]]


async def _judge_alternative(
    llm: LLMClient,
    plan: AnalysisPlan,
    emitter: RunEmitter,
    step: Step,
    option: Option,
    ledger: JudgedLedger | None = None,
    memory: RunMemory | None = None,
) -> tuple[Option | None, str]:
    judgement = memory.recall_verdict(plan, step, option) if memory else None
    try:
        if judgement is None:
            judgement = await judge_option(llm, plan, step, option, "planner")
            if memory is not None:
                memory.remember_verdict(plan, step, option, judgement)
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
        return None, data.reason
    data = OptionJudgedData(
        step_id=step.id,
        option_id=option.id,
        defensibility=judgement.defensibility,
        accepted=judgement.accepted,
        reason=judgement.reason,
        origin="planner",
    )
    await emitter.emit("option.judged", data.model_dump(mode="json"))
    if ledger is not None:
        ledger.record(step.id, option, judgement)
    if not judgement.accepted:
        return None, judgement.reason
    accepted = option.model_copy(
        update={
            "defensibility": judgement.defensibility,
            "source": option.source or judgement.source,
        }
    )
    return accepted, judgement.reason


async def _refill_step(
    llm: LLMClient,
    plan: AnalysisPlan,
    emitter: RunEmitter,
    summary: CodingSummary,
    step: Step,
    rejected: Rejected,
    ledger: JudgedLedger | None,
    memory: RunMemory | None,
    screen: Screen | None,
) -> None:
    options = await propose_refill(llm, plan, step, rejected)
    if screen is not None:
        options = await screen(step.id, options)
    judged = await gather_cancelling(
        _judge_alternative(llm, plan, emitter, step, option, ledger, memory) for option in options
    )
    kept = [option for option, _ in judged if option is not None]
    summary.options_dropped_by_judge += len(judged) - len(kept)
    summary.options_added_after_judge += len(kept)
    step.options.extend(kept)


async def judge_plan_options(
    llm: LLMClient,
    plan: AnalysisPlan,
    emitter: RunEmitter,
    summary: CodingSummary,
    ledger: JudgedLedger | None = None,
    memory: RunMemory | None = None,
    screen: Screen | None = None,
) -> None:
    """Judge every non-default planner option and drop the rejected ones before any coding.

    When the rejections leave the plan too few branching steps, the planner proposes new
    alternatives once for each step that lost all of them, and those are judged in turn.
    """
    targets = [(s, o) for s in plan.steps for o in s.options if not o.is_default]
    if not targets:
        return
    before = {step.id: len(step.options) for step in plan.steps}
    outcomes = await gather_cancelling(
        _judge_alternative(llm, plan, emitter, step, option, ledger, memory)
        for step, option in targets
    )
    replaced = {
        (step.id, option.id): judged
        for (step, option), (judged, _) in zip(targets, outcomes, strict=True)
    }
    rejected: dict[str, Rejected] = {}
    for (step, option), (judged, reason) in zip(targets, outcomes, strict=True):
        if judged is None:
            rejected.setdefault(step.id, []).append((option, reason))
    for step in plan.steps:
        step.options = [
            replaced.get((step.id, o.id), o)
            for o in step.options
            if replaced.get((step.id, o.id), o) is not None
        ]
    summary.options_dropped_by_judge += sum(len(r) for r in rejected.values())
    await gather_cancelling(
        _refill_step(llm, plan, emitter, summary, step, rejected[step.id], ledger, memory, screen)
        for step in collapsed_steps(plan, before)
    )
    await publish_plan(emitter, plan)
