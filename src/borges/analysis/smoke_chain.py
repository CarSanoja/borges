from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from borges.analysis.models import Step
from borges.analysis.smoke_core import smoke_option
from borges.analysis.smoke_types import Repair, SmokeConfig
from borges.sandbox.backend import Checkpoint


def emptied(effects: dict[str, Any] | None) -> bool:
    return bool(effects) and (effects or {}).get("rows_after") == 0


async def model_input(
    config: SmokeConfig,
    repair: Repair,
    between: Sequence[Step],
    start: Checkpoint,
    effects: dict[str, Any] | None = None,
) -> Checkpoint | None:
    """The model's sample input after `between`, or None when it cannot be built or is empty."""
    if emptied(effects):
        return None
    isolated = replace(config, larger=None)
    checkpoint = start
    for step in between:
        default = config.state.defaults.get(step.id)
        if default is None:
            return None
        tried = await smoke_option(isolated, repair, checkpoint, step, default.option, budget=0)
        if tried.status == "failed" or tried.checkpoint is None or emptied(tried.effects):
            return None
        checkpoint = tried.checkpoint
    return checkpoint
