from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import replace

from borges.analysis.models import Step
from borges.analysis.smoke_model_input import model_inputs
from borges.analysis.smoke_model_repair import MODEL_DROPPED_NOTE, _repaired_model
from borges.analysis.smoke_types import Outcome, Repair, SmokeConfig
from borges.analysis.smoke_upstream import DROPPED_NOTE, _probe, _repaired, _short, probe_option


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


async def probe_extra_model(
    config: SmokeConfig, repair: Repair, steps: Sequence[Step], step: Step, outcome: Outcome
) -> Outcome:
    """Run an extra model option after the alternatives of the earlier steps, as the plan's own
    model options are run. A red_cards adversary logit at 9b95d04 passed on the default path and
    failed in four universes, where the extended covariates added a text column."""
    ids = [s.id for s in steps]
    if step.kind != "model" or step.id not in ids:
        return outcome
    inputs = await model_inputs(config, repair, list(steps), ids.index(step.id))
    errors = await asyncio.gather(
        *(probe_option(config, repair, step, outcome.option, i.checkpoint) for i in inputs)
    )
    failures = [
        (item, steps[item.index], error)
        for item, error in zip(inputs, errors, strict=True)
        if error is not None
    ]
    if not failures:
        return outcome
    fresh = await _repaired_model(config, repair, step, outcome, failures)
    if fresh is not None:
        return fresh
    item, upstream, error = failures[0]
    note = MODEL_DROPPED_NOTE.format(
        label=outcome.option.label,
        upstream=item.outcome.option.label,
        title=upstream.title,
        error=_short(error),
    )
    return replace(outcome, status="failed", error=note)
