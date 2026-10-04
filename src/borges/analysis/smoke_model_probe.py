from __future__ import annotations

import asyncio

from borges.analysis.models import CodingSummary, Option, Step
from borges.analysis.smoke_model_input import Fault, ModelInput, model_inputs
from borges.analysis.smoke_model_repair import handle_model
from borges.analysis.smoke_types import Repair, SmokeConfig
from borges.analysis.smoke_upstream import _handle, probe_option

MAX_MODEL_OPTIONS = 6


async def _run(
    config: SmokeConfig, repair: Repair, model: Step, options: list[Option], item: ModelInput
) -> list[str | None]:
    return list(
        await asyncio.gather(
            *(probe_option(config, repair, model, o, item.checkpoint) for o in options)
        )
    )


async def probe_model(
    config: SmokeConfig,
    repair: Repair,
    steps: list[Step],
    index: int,
    summary: CodingSummary | None,
) -> None:
    model = steps[index]
    if model.id not in config.state.defaults or model.id not in config.state.parents:
        return
    inputs = await model_inputs(config, repair, steps, index)
    if not inputs:
        return
    default = config.state.defaults[model.id].option
    others = [
        o.option
        for o in config.state.outcomes.get(model.id, [])
        if o.status != "failed" and o.option.id != default.id
    ][:MAX_MODEL_OPTIONS]
    runs = await asyncio.gather(
        *(_run(config, repair, model, [default, *others], i) for i in inputs)
    )
    culprits: dict[tuple[int, str], tuple[ModelInput, str]] = {}
    faults: dict[str, list[Fault]] = {}
    for item, errors in zip(inputs, runs, strict=True):
        if errors[0] is not None:
            culprits.setdefault((item.index, item.outcome.option.id), (item, errors[0]))
            continue
        for option, error in zip(others, errors[1:], strict=True):
            if error is not None:
                faults.setdefault(option.id, []).append((item, steps[item.index], error))
    await asyncio.gather(
        *(
            _handle(
                config,
                repair,
                steps[item.index],
                model,
                item.outcome,
                error,
                summary,
                steps[item.index + 1 : index],
            )
            for item, error in culprits.values()
        )
    )
    by_id = {o.option.id: o for o in config.state.outcomes.get(model.id, [])}
    await asyncio.gather(
        *(
            handle_model(config, repair, model, by_id[oid], failures, summary)
            for oid, failures in faults.items()
            if oid in by_id
        )
    )
