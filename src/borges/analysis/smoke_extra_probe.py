from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from borges.analysis.models import Step
from borges.analysis.smoke_types import Outcome, Repair, SmokeConfig
from borges.analysis.smoke_upstream import DROPPED_NOTE, _probe, _repaired, _short


async def probe_extra(
    config: SmokeConfig, repair: Repair, steps: Sequence[Step], step: Step, outcome: Outcome
) -> Outcome:
    """Run the model's default after an extra option of an earlier step, as the plan probe does."""
    ids = [s.id for s in steps]
    model = next((s for s in steps if s.kind == "model"), None)
    if (
        step.kind == "model"
        or outcome.checkpoint is None
        or model is None
        or step.id not in ids
        or model.id not in config.state.defaults
        or step.id not in config.state.parents
    ):
        return outcome
    between = list(steps[ids.index(step.id) + 1 : ids.index(model.id)])
    error = await _probe(config, repair, model, outcome, between, every=True)
    if error is None:
        return outcome
    fresh = await _repaired(config, repair, step, model, outcome, error, between, every=True)
    if fresh is not None:
        return fresh
    note = DROPPED_NOTE.format(label=outcome.option.label, title=step.title, error=_short(error))
    return replace(outcome, status="failed", error=note)
