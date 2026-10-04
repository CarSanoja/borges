from __future__ import annotations

from collections.abc import Awaitable, Callable

from borges.analysis.models import Step
from borges.analysis.smoke_replan import has_survivor
from borges.analysis.smoke_types import Outcome, SmokeConfig
from borges.sandbox.backend import Checkpoint

Round = Callable[[Checkpoint], Awaitable[list[Outcome]]]

NOTE = (
    "No option of the step '{step}' ran after the default '{old}' of the step '{earlier}', so "
    "'{new}' became that step's default and the step ran after it."
)


async def rescue_by_upstream_default(
    config: SmokeConfig, earlier: Step, step: Step, run: Round
) -> tuple[Checkpoint, list[Outcome]] | None:
    """Try each other surviving option of the previous step as its default; keep the first that
    lets an option of this step pass."""
    current = config.state.defaults.get(earlier.id)
    if current is None:
        return None
    for outcome in config.state.outcomes.get(earlier.id, []):
        if outcome.checkpoint is None or outcome.option.id == current.option.id:
            continue
        outcomes = await run(outcome.checkpoint)
        if not has_survivor(outcomes):
            continue
        for option in earlier.options:
            option.is_default = option.id == outcome.option.id
        config.state.defaults[earlier.id] = outcome
        config.state.notes.append(
            NOTE.format(
                step=step.title,
                old=current.option.label,
                earlier=earlier.title,
                new=outcome.option.label,
            )
        )
        return outcome.checkpoint, outcomes
    return None
