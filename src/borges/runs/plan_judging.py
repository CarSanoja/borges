from __future__ import annotations

from collections.abc import Awaitable, Callable

from borges.analysis.judge import JudgeOrigin, judge_option
from borges.analysis.models import AnalysisPlan, CodingSummary, Option, Step
from borges.analysis.plan_refill import Rejected, collapsed_steps, propose_refill
from borges.llm.client import BudgetExceeded, LLMClient
from borges.llm.gather import gather_cancelling
from borges.memory.run_memory import RunMemory
from borges.runs.default_judging import replace_default
from borges.runs.emitter import RunEmitter
from borges.runs.events import OptionJudgedData
from borges.runs.judged_ledger import JudgedLedger
from borges.runs.runner import publish_plan

Screen = Callable[[str, list[Option]], Awaitable[list[Option]]]
JUDGE_FAILED = "judge failed"


async def _judge_alternative(
    llm: LLMClient,
    plan: AnalysisPlan,
    emitter: RunEmitter,
    step: Step,
    option: Option,
    ledger: JudgedLedger | None = None,
    memory: RunMemory | None = None,
    origin: JudgeOrigin = "planner",
) -> tuple[Option | None, str]:
    judgement = memory.recall_verdict(plan, step, option) if memory else None
    try:
        if judgement is None:
            judgement = await judge_option(llm, plan, step, option, origin)
            if memory is not None:
                memory.remember_verdict(plan, step, option, judgement)
    except BudgetExceeded:
        raise
    except Exception as exc:
        if origin == "default":
            return None, f"{JUDGE_FAILED}: {exc}"
        data = OptionJudgedData(
            step_id=step.id,
            option_id=option.id,
            defensibility=0.0,
            accepted=False,
            reason=f"{JUDGE_FAILED}: {exc}",
            origin=origin,
        )
        await emitter.emit("option.judged", data.model_dump(mode="json"))
        return None, data.reason
    data = OptionJudgedData(
        step_id=step.id,
        option_id=option.id,
        defensibility=judgement.defensibility,
        accepted=judgement.accepted,
        reason=judgement.reason,
        origin=origin,
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
    keep_defaults: bool = False,
) -> None:
    """Judge every planner option, the conventional ones included, before any coding.

    A rejected alternative is dropped. When the rejections leave the plan too few branching
    steps, the planner proposes new alternatives once for each step that lost all of them,
    and those are judged in turn. A rejected conventional option is then replaced (see
    default_judging.replace_default); a judge failure never replaces one. When the defaults are
    the user's own analysis (keep_defaults), a rejected one is kept and the judge's reason is
    recorded, because the run asks how fragile that analysis is.
    """
    defaults = getattr(llm, "judges_defaults", True)
    targets = [(s, o) for s in plan.steps for o in s.options if defaults or not o.is_default]
    if not targets:
        return
    before = {step.id: len(step.options) for step in plan.steps}
    outcomes = await gather_cancelling(
        _judge_alternative(llm, plan, emitter, step, option, ledger, memory, _origin(option))
        for step, option in targets
    )
    replaced: dict[tuple[str, str], Option | None] = {}
    rejected: dict[str, Rejected] = {}
    disputed: dict[str, str] = {}
    for (step, option), (judged, reason) in zip(targets, outcomes, strict=True):
        if option.is_default:
            if judged is None and not reason.startswith(JUDGE_FAILED):
                disputed[step.id] = reason
            continue
        replaced[(step.id, option.id)] = judged
        if judged is None:
            rejected.setdefault(step.id, []).append((option, reason))
    for step in plan.steps:
        step.options = [
            replaced.get((step.id, o.id), o)
            for o in step.options
            if replaced.get((step.id, o.id), o) is not None
        ]
    summary.options_dropped_by_judge += sum(len(r) for r in rejected.values())
    if keep_defaults:
        summary.defaults_kept.extend(
            f"{step_id}: {plan.step(step_id).default.label}: {reason}"
            for step_id, reason in disputed.items()
        )
        disputed = {}
    await gather_cancelling(
        _refill_step(llm, plan, emitter, summary, step, rejected[step.id], ledger, memory, screen)
        for step in collapsed_steps(plan, before)
    )
    await gather_cancelling(
        replace_default(
            llm,
            plan,
            summary,
            plan.step(step_id),
            reason,
            lambda step, option: _judge_alternative(
                llm, plan, emitter, step, option, ledger, memory
            ),
        )
        for step_id, reason in disputed.items()
    )
    await publish_plan(emitter, plan)


def _origin(option: Option) -> JudgeOrigin:
    return "default" if option.is_default else "planner"
