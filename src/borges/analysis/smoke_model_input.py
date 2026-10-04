from __future__ import annotations

import asyncio
from dataclasses import dataclass

from borges.analysis.models import Step
from borges.analysis.smoke_chain import model_input
from borges.analysis.smoke_types import Outcome, Repair, SmokeConfig
from borges.sandbox.backend import Checkpoint

MAX_INPUTS = 6


@dataclass
class ModelInput:
    index: int
    outcome: Outcome
    checkpoint: Checkpoint


Fault = tuple[ModelInput, Step, str]


def _alternatives(config: SmokeConfig, step: Step) -> list[Outcome]:
    current = config.state.defaults.get(step.id)
    default_id = current.option.id if current is not None else step.default.id
    return [
        o
        for o in config.state.outcomes.get(step.id, [])
        if o.status != "failed" and o.checkpoint is not None and o.option.id != default_id
    ]


async def model_inputs(
    config: SmokeConfig, repair: Repair, steps: list[Step], index: int
) -> list[ModelInput]:
    picked: list[tuple[int, Outcome]] = []
    for k in range(index - 1, -1, -1):
        if steps[k].id not in config.state.parents:
            continue
        room = MAX_INPUTS - len(picked)
        picked += [(k, o) for o in _alternatives(config, steps[k])[:room]]
    built = await asyncio.gather(
        *(
            model_input(config, repair, steps[k + 1 : index], o.checkpoint)
            for k, o in picked
            if o.checkpoint
        )
    )
    return [ModelInput(k, o, c) for (k, o), c in zip(picked, built, strict=True) if c]
