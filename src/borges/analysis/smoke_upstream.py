from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import replace

from borges.analysis.models import CodingSummary, Option, Step
from borges.analysis.smoke_chain import model_input
from borges.analysis.smoke_collision import resolve_extra
from borges.analysis.smoke_core import smoke_option
from borges.analysis.smoke_larger import is_sample_artefact, smoke_rows
from borges.analysis.smoke_review import _re_review
from borges.analysis.smoke_types import Outcome, Repair, SmokeConfig
from borges.llm.client import LLMError
from borges.sandbox.backend import Checkpoint

MAX_PROBED = 4
SHORT_ERROR_CHARS = 160

REPAIR_MESSAGE = (
    "With this option the next step, the model step '{title}', fails on the sample with:\n"
    "{error}\n"
    "Change this option so that the data and ctx it leaves behind work for the model step, "
    "for example by only naming columns that exist at this point."
)
DROPPED_NOTE = (
    "The option '{label}' of the step '{title}' was dropped: with it the model step fails on "
    "the sample ({error})."
)
CAUGHT_NOTE = (
    "caught upstream: with the original code the model step failed on the sample ({error})"
)


def _short(error: str) -> str:
    first = error.strip().splitlines()[0] if error.strip() else "unknown error"
    return first[:SHORT_ERROR_CHARS]


async def probe_option(
    config: SmokeConfig, repair: Repair, model: Step, option: Option, checkpoint: Checkpoint
) -> str | None:
    isolated = replace(config, larger=None)
    tried = await smoke_option(isolated, repair, checkpoint, model, option, budget=0)
    if tried.status != "failed" or is_sample_artefact(tried.error):
        return None
    return tried.error or "unknown error"


async def _probe(
    config: SmokeConfig,
    repair: Repair,
    model: Step,
    outcome: Outcome,
    between: Sequence[Step] = (),
) -> str | None:
    assert outcome.checkpoint is not None
    checkpoint = await model_input(config, repair, between, outcome.checkpoint)
    if checkpoint is None:
        return None
    default = config.state.defaults[model.id]
    return await probe_option(config, repair, model, default.option, checkpoint)


async def _repaired(
    config: SmokeConfig,
    repair: Repair,
    previous: Step,
    model: Step,
    outcome: Outcome,
    error: str,
    between: Sequence[Step] = (),
) -> Outcome | None:
    parent = config.state.parents[previous.id]
    message = REPAIR_MESSAGE.format(title=model.title, error=error)
    try:
        code, violation, name = await repair(previous, outcome.option, message, outcome.attempts)
    except LLMError:
        return None
    if violation is not None:
        return None
    option = outcome.option.model_copy(update={"code": code})
    tried = await smoke_option(config, repair, parent, previous, option, budget=0)
    if tried.status == "failed":
        return None
    tried = await _re_review(config, previous, tried)
    if tried.status != "failed":
        tried = await resolve_extra(config, repair, parent, previous, tried)
    if tried.status == "failed" or await _probe(config, repair, model, tried, between) is not None:
        return None
    return Outcome(
        tried.option,
        "repaired",
        outcome.attempts + 1,
        None,
        tried.checkpoint,
        [*outcome.models, name],
        tried.effects,
        tried.result,
        sample_rows=tried.sample_rows,
    )


async def _handle(
    config: SmokeConfig,
    repair: Repair,
    previous: Step,
    model: Step,
    outcome: Outcome,
    error: str,
    summary: CodingSummary | None,
    between: Sequence[Step] = (),
) -> None:
    fresh = await _repaired(config, repair, previous, model, outcome, error, between)
    outcomes = config.state.outcomes[previous.id]
    if fresh is not None:
        if summary is not None:
            summary.repaired_after_smoke += 1
        previous.options = [
            fresh.option if o.id == fresh.option.id else o for o in previous.options
        ]
        config.state.outcomes[previous.id] = [
            fresh if o.option.id == fresh.option.id else o for o in outcomes
        ]
        if config.on_smoke is not None:
            await config.on_smoke(
                previous.id,
                fresh.option.id,
                "repaired",
                fresh.attempts,
                CAUGHT_NOTE.format(error=_short(error)),
                fresh.models,
                *smoke_rows(fresh),
            )
        return
    option = outcome.option
    previous.options = [o for o in previous.options if o.id != option.id]
    config.state.outcomes[previous.id] = [o for o in outcomes if o.option.id != option.id]
    note = DROPPED_NOTE.format(label=option.label, title=previous.title, error=_short(error))
    config.state.notes.append(note)
    if summary is not None:
        summary.failed += 1
    if config.on_smoke is not None:
        await config.on_smoke(
            previous.id, option.id, "failed", outcome.attempts, note, outcome.models
        )


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
    await asyncio.gather(
        *(_handle(config, repair, previous, model, o, e, summary) for o, e in failing)
    )
