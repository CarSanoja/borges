from __future__ import annotations

from dataclasses import dataclass
from functools import partial

from borges.analysis.models import Option, Step
from borges.analysis.smoke_default_rescue import (
    Plain,
    Round,
    Settled,
    rescue_by_upstream_default,
)
from borges.analysis.smoke_left_out import leave_out
from borges.analysis.smoke_replan import has_survivor, replan_outcomes
from borges.analysis.smoke_types import Outcome, Replan, SmokeConfig
from borges.llm.client import LLMError
from borges.sandbox.backend import Checkpoint


@dataclass
class Tools:
    run: Round
    plain: Plain


def _union(first: list[Option], later: list[Option]) -> list[Option]:
    seen = {o.id for o in first}
    extra = [o.model_copy(update={"is_default": False}) for o in later if o.id not in seen]
    return [*first, *extra]


async def _without_previous(
    config: SmokeConfig, earlier: Step, step: Step, options: list[Option], tools: Tools
) -> Settled | None:
    """Last resort for the model step: leave the previous data step out if the model then runs."""
    before = config.state.parents.get(earlier.id)
    if before is None:
        return None
    current = step.options
    step.options = options
    if not await tools.plain(before):
        step.options = current
        return None
    failed = [o for o in config.state.outcomes.get(earlier.id, [])]
    left = await leave_out(config, earlier, before, failed)
    if left is None or left.checkpoint is None:
        step.options = current
        return None
    config.state.defaults[earlier.id] = left
    config.state.outcomes[earlier.id] = [left]
    outcomes = await tools.run(left.checkpoint)
    return left.checkpoint, outcomes


async def settle(
    config: SmokeConfig,
    replan: Replan | None,
    steps: list[Step],
    index: int,
    parent: Checkpoint,
    outcomes: list[Outcome],
    tools: Tools,
) -> Settled:
    """What is tried, cheapest first, when no option of a step passed its smoke run."""
    step = steps[index]
    earlier = steps[index - 1] if index > 0 else None
    first = list(step.options)
    if earlier is not None:
        rescued = await rescue_by_upstream_default(config, earlier, step, tools.plain, tools.run)
        if rescued is not None:
            return rescued
    if replan is None:
        return parent, outcomes
    failure: LLMError | None = None
    try:
        outcomes = await replan_outcomes(config, replan, step, outcomes, partial(tools.run, parent))
    except LLMError as exc:
        failure = exc
    if has_survivor(outcomes):
        return parent, outcomes
    if earlier is not None and failure is not None:
        rescued = await rescue_by_upstream_default(config, earlier, step, tools.plain, tools.run)
        if rescued is not None:
            return rescued
    if step.kind == "model" and earlier is not None:
        options = _union(first, step.options)
        skipped = await _without_previous(config, earlier, step, options, tools)
        if skipped is not None and has_survivor(skipped[1]):
            return skipped
    if step.kind != "model":
        left = await leave_out(config, step, parent, outcomes)
        if left is not None:
            return parent, [left]
    if failure is not None:
        raise failure
    return parent, outcomes
