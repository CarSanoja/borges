from __future__ import annotations

import asyncio

from borges.analysis.models import CodingSummary, Step
from borges.analysis.smoke_default_encoding import repair_default, text_fault
from borges.analysis.smoke_model_input import Fault, ModelInput
from borges.analysis.smoke_types import Repair, SmokeConfig
from borges.analysis.smoke_upstream import MAX_PROBED, _handle, _probe


async def probe_upstream(
    config: SmokeConfig,
    repair: Repair,
    previous: Step,
    model: Step,
    summary: CodingSummary | None,
) -> None:
    if model.id not in config.state.defaults or previous.id not in config.state.parents:
        return
    default_id = previous.default.id
    alternatives = [
        o
        for o in config.state.outcomes.get(previous.id, [])
        if o.status != "failed" and o.checkpoint is not None and o.option.id != default_id
    ][:MAX_PROBED]
    errors = await asyncio.gather(*(_probe(config, repair, model, o) for o in alternatives))
    failing = [(o, e) for o, e in zip(alternatives, errors, strict=True) if e is not None]
    text: list[Fault] = [
        (ModelInput(-1, o, o.checkpoint), previous, e) for o, e in failing if text_fault(e)
    ]
    if text and await repair_default(config, repair, model, text, summary):
        failing = [(o, e) for o, e in failing if not text_fault(e)]
    await asyncio.gather(
        *(_handle(config, repair, previous, model, o, e, summary) for o, e in failing)
    )
