from __future__ import annotations

from collections.abc import Sequence

from borges.analysis.models import Option, Step
from borges.analysis.smoke_collision import remember_extra, resolve_extra
from borges.analysis.smoke_core import smoke_option
from borges.analysis.smoke_extra_probe import probe_extra, probe_extra_model
from borges.analysis.smoke_orientation import orientation_check
from borges.analysis.smoke_review import review_extra
from borges.analysis.smoke_types import Outcome, Repair, SmokeConfig


async def smoke_extra_option(
    config: SmokeConfig, repair: Repair, step: Step, option: Option, steps: Sequence[Step] = ()
) -> Outcome | None:
    parent = config.state.parents.get(step.id)
    default = config.state.defaults.get(step.id)
    if parent is None or default is None:
        return None
    check = orientation_check(config, step, option.id)
    outcome = await smoke_option(config, repair, parent, step, option, check)
    if outcome.status != "failed":
        outcome = await resolve_extra(config, repair, parent, step, outcome)
    if outcome.status != "failed":
        outcome = await probe_extra(config, repair, steps, step, outcome)
    if outcome.status != "failed":
        outcome = await probe_extra_model(config, repair, steps, step, outcome)
    if config.on_smoke is not None:
        await config.on_smoke(
            step.id,
            outcome.option.id,
            outcome.status,
            outcome.attempts,
            outcome.error,
            outcome.models,
        )
    if outcome.status == "failed":
        return outcome
    reviewed = await review_extra(config, repair, parent, step, default, outcome)
    if reviewed.status != "failed":
        remember_extra(config, step, reviewed)
    return reviewed
