from __future__ import annotations

import asyncio
from functools import partial
from typing import Any

import numpy as np

from borges.analysis.models import CodingSummary, Step
from borges.analysis.smoke_core import smoke_option
from borges.analysis.smoke_larger import smoke_rows
from borges.analysis.smoke_origin import probe_pairs, shifted_error
from borges.analysis.smoke_types import Check, Outcome, Repair, SmokeConfig
from borges.sandbox.backend import Checkpoint

REVERSED_BELOW = -0.3

REVERSED_TEMPLATE = (
    "column '{name}' is reversed relative to the default option (correlation {r:.2f} on the "
    "same rows): keep the same direction as the default (for a PCA or factor score flip the "
    "sign when it correlates negatively with the mean of its items, decided by the data and "
    "never by a fixed -1; never swap groups or reverse a coding)"
)


def probe_correlation(
    default: dict[str, Any] | None, other: dict[str, Any] | None, name: str
) -> float | None:
    pairs = probe_pairs(default, other, name)
    if pairs is None:
        return None
    xs, ys = pairs
    if np.std(xs) == 0 or np.std(ys) == 0:
        return None
    return float(np.corrcoef(xs, ys)[0, 1])


def produced_names(produces: list[str], default: dict[str, Any] | None) -> list[str]:
    if produces:
        return list(produces)
    return list((default or {}).get("added") or [])


def orientation_error(
    names: list[str],
    default: dict[str, Any] | None,
    other: dict[str, Any] | None,
    cut: set[str] | frozenset[str] = frozenset(),
) -> str | None:
    for name in names:
        r = probe_correlation(default, other, name)
        if r is not None and r < REVERSED_BELOW:
            return REVERSED_TEMPLATE.format(name=name, r=r)
        shifted = shifted_error(name, default, other) if name in cut else None
        if shifted is not None:
            return shifted
    return None


def orientation_check(config: SmokeConfig, step: Step, option_id: str) -> Check | None:
    """The orientation check for one option of a step, against the step's live default."""
    default = config.state.defaults.get(step.id)
    if default is None or step.kind == "model" or default.option.id == option_id:
        return None
    names = produced_names(step.produces, default.effects)
    if not names:
        return None
    return partial(orientation_error, names, default.effects, cut=config.state.cut)


def effective_default(step: Step, outcomes: list[Outcome]) -> Outcome | None:
    alive = {o.option.id: o for o in outcomes if o.status != "failed"}
    chosen = alive.get(step.default.id)
    if chosen is not None:
        return chosen
    return next((alive[o.id] for o in step.options if o.id in alive), None)


async def notify_changed(
    config: SmokeConfig, summary: CodingSummary | None, step: Step, before: Outcome, after: Outcome
) -> None:
    if summary is not None:
        repaired = before.status == "passed" and after.status == "repaired"
        summary.repaired_after_smoke += int(repaired)
        summary.failed += int(after.status == "failed")
    if config.on_smoke is not None:
        await config.on_smoke(
            step.id,
            after.option.id,
            after.status,
            after.attempts,
            after.error,
            after.models,
            *smoke_rows(after),
        )


async def apply_orientation(
    config: SmokeConfig,
    repair: Repair,
    parent: Checkpoint,
    step: Step,
    outcomes: list[Outcome],
    summary: CodingSummary | None,
) -> list[Outcome]:
    default = effective_default(step, outcomes)
    if default is None or step.kind == "model":
        return outcomes
    names = produced_names(step.produces, default.effects)
    if not names:
        return outcomes

    def check(effects: dict[str, Any] | None) -> str | None:
        return orientation_error(names, default.effects, effects, config.state.cut)

    async def one(outcome: Outcome) -> Outcome:
        if outcome is default or outcome.status == "failed":
            return outcome
        error = check(outcome.effects)
        if error is None:
            return outcome
        resume = (outcome.attempts, outcome.models, error)
        updated = await smoke_option(
            config, repair, parent, step, outcome.option, check, resume=resume
        )
        await notify_changed(config, summary, step, outcome, updated)
        return updated

    return list(await asyncio.gather(*(one(o) for o in outcomes)))
