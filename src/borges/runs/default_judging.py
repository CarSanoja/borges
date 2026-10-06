from __future__ import annotations

from collections.abc import Awaitable, Callable

from borges.analysis.models import AnalysisPlan, CodingSummary, Option, Step
from borges.analysis.plan_refill import propose_refill
from borges.llm.client import LLMClient
from borges.llm.gather import gather_cancelling

JudgeOne = Callable[[Step, Option], Awaitable[tuple[Option | None, str]]]


async def replace_default(
    llm: LLMClient,
    plan: AnalysisPlan,
    summary: CodingSummary,
    step: Step,
    reason: str,
    judge: JudgeOne,
) -> None:
    """Replace a conventional option the judge rejected.

    The new conventional option is the accepted alternative of the step with the highest
    defensibility. Without one, the planner proposes alternatives once and those the judge
    accepts become the candidates. When none is accepted the old option stays and the run
    records that the judge disputes it.
    """
    old = step.default
    candidates = [o for o in step.options if not o.is_default]
    if not candidates:
        proposed = await propose_refill(llm, plan, step, [(old, reason)])
        judged = await gather_cancelling(judge(step, option) for option in proposed)
        candidates = [option for option, _ in judged if option is not None]
        step.options.extend(candidates)
    if not candidates:
        summary.defaults_disputed.append(f"{step.id}: {old.label}: {reason}")
        return
    best = max(candidates, key=lambda o: o.defensibility or 0.0)
    step.options = [
        o.model_copy(update={"is_default": o.id == best.id}) for o in step.options if o.id != old.id
    ]
    summary.defaults_replaced.append(f"{step.id}: {old.label} -> {best.label}: {reason}")
