from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from borges.analysis.models import Step
from borges.analysis.smoke_core import smoke_option
from borges.analysis.smoke_types import Repair, SmokeConfig
from borges.sandbox.backend import Checkpoint


async def model_input(
    config: SmokeConfig, repair: Repair, between: Sequence[Step], start: Checkpoint
) -> Checkpoint | None:
    isolated = replace(config, larger=None)
    checkpoint = start
    for step in between:
        default = config.state.defaults.get(step.id)
        if default is None:
            return None
        tried = await smoke_option(isolated, repair, checkpoint, step, default.option, budget=0)
        if tried.status == "failed" or tried.checkpoint is None:
            return None
        checkpoint = tried.checkpoint
    return checkpoint
