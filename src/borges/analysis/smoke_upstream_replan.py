"""A model that fails because the step before it built a constant, re-planned at that step.

In fert10 on 7 Oct the fertility step put ovulation fourteen days before the last period, so
DateTesting never fell in the window and fertility_high was 0 in every row, under both of its
options. The model template said so (INPUT_FAULT), the model's repairs stopped as they should,
and the one re-plan went to the model step, which was never the problem. The planner is asked
once more for the step that builds the model's input, with the model's error as the reason.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from borges.analysis.model_spec.render_design import INPUT_FAULT
from borges.analysis.models import Step
from borges.analysis.smoke_orientation import effective_default
from borges.analysis.smoke_replan import has_survivor
from borges.analysis.smoke_types import Outcome, Replan, SmokeConfig
from borges.llm.client import LLMError
from borges.sandbox.backend import Checkpoint

FAULT_CHARS = 400
FAULT_MESSAGE = (
    "With this option the model step '{title}' fails on the sample: {error} Rebuild the "
    "column so that it takes different values across the rows, as the question compares them."
)
REPLANNED_NOTE = (
    "The model step '{title}' failed on the sample because the step '{earlier}' built a "
    "constant input; the planner re-planned '{earlier}' once and proposed: {proposed}."
)

StepRound = Callable[[], Awaitable[list[Outcome]]]
ModelRound = Callable[[Checkpoint], Awaitable[list[Outcome]]]


def input_fault(outcomes: list[Outcome]) -> str | None:
    return next((o.error for o in outcomes if o.error and INPUT_FAULT in o.error), None)


async def replan_upstream(
    config: SmokeConfig,
    replan: Replan | None,
    earlier: Step,
    model: Step,
    outcomes: list[Outcome],
    run_earlier: StepRound,
    run_model: ModelRound,
) -> tuple[Checkpoint, list[Outcome]] | None:
    fault = input_fault(outcomes)
    previous = config.state.outcomes.get(earlier.id, [])
    if fault is None or replan is None or not previous:
        return None
    reason = FAULT_MESSAGE.format(title=model.title, error=fault[:FAULT_CHARS])
    failed = [Outcome(o.option, "failed", o.attempts, reason, None, o.models) for o in previous]
    try:
        replanned = await replan(earlier, failed)
    except LLMError:
        return None
    if replanned is None or not replanned.options:
        return None
    kept = (earlier.options, config.state.defaults.get(earlier.id), previous)
    earlier.options = replanned.options
    survivors = [o for o in await run_earlier() if o.status != "failed"]
    default = effective_default(earlier, survivors)
    model_outcomes = await run_model(default.checkpoint) if default and default.checkpoint else []
    if default is None or not has_survivor(model_outcomes):
        earlier.options = kept[0]
        return None
    earlier.options = [o.option for o in survivors]
    for option in earlier.options:
        option.is_default = option.id == default.option.id
    config.state.defaults[earlier.id] = default
    config.state.outcomes[earlier.id] = survivors
    proposed = ", ".join(o.id for o in replanned.options)
    config.state.notes.append(
        REPLANNED_NOTE.format(title=model.title, earlier=earlier.id, proposed=proposed)
    )
    if config.on_replan is not None:
        await config.on_replan(earlier.id, [o.option.id for o in previous], proposed.split(", "))
    assert default.checkpoint is not None
    return default.checkpoint, model_outcomes
