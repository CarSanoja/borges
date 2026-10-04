from __future__ import annotations

import asyncio
from typing import Any

from borges.analysis.models import CodingSummary, Step
from borges.analysis.prompts.coder_collision import COLLISION, SCALE
from borges.analysis.smoke_core import smoke_option
from borges.analysis.smoke_larger import smoke_rows
from borges.analysis.smoke_orientation import effective_default, orientation_error, produced_names
from borges.analysis.smoke_output_checks import find_pairs, predicate, same_output
from borges.analysis.smoke_output_notes import applied_note, unresolved_note
from borges.analysis.smoke_review import _re_review
from borges.analysis.smoke_types import Outcome, Repair, SmokeConfig
from borges.llm.client import LLMError
from borges.sandbox.backend import Checkpoint


async def _rewrite(
    config: SmokeConfig,
    repair: Repair,
    parent: Checkpoint,
    step: Step,
    target: Outcome,
    other: Outcome,
    kind: str,
    summary: CodingSummary | None,
    default: Outcome | None,
) -> Outcome:
    assert config.rewrite is not None
    try:
        code, violation, model = await config.rewrite(step, target.option, other.option, kind)
    except LLMError:
        return target
    if violation is not None:
        return target
    option = target.option.model_copy(update={"code": code})
    names = produced_names(step.produces, default.effects) if default is not None else []

    def check(effects: dict[str, Any] | None) -> str | None:
        if default is None or target is default or not names:
            return None
        return orientation_error(names, default.effects, effects)

    tried = await smoke_option(
        config, repair, parent, step, option, check if names else None, budget=0
    )
    if tried.status == "failed" or same_output(step, tried, target):
        return target
    tried = await _re_review(config, step, tried)
    if tried.status == "failed":
        return target
    fresh = Outcome(
        tried.option,
        "repaired",
        target.attempts + 1,
        None,
        tried.checkpoint,
        [*target.models, model],
        tried.effects,
        tried.result,
        sample_rows=tried.sample_rows,
    )
    if summary is not None:
        summary.options_recoded_by_output_check += 1
    if config.on_smoke is not None:
        await config.on_smoke(
            step.id,
            fresh.option.id,
            fresh.status,
            fresh.attempts,
            applied_note(kind, target, other),
            fresh.models,
            *smoke_rows(fresh),
        )
    return fresh


def _record_unresolved(
    config: SmokeConfig, kind: str, step: Step, pairs: list[tuple[Outcome, Outcome]]
) -> None:
    for a, b in pairs:
        config.state.notes.append(unresolved_note(kind, step, a, b, config.metric))


async def _resolve(
    config: SmokeConfig,
    repair: Repair,
    parent: Checkpoint,
    step: Step,
    outcomes: list[Outcome],
    summary: CodingSummary | None,
    kind: str,
) -> list[Outcome]:
    live = [o for o in outcomes if o.status != "failed"]
    pairs = find_pairs(kind, step, live)
    if not pairs:
        return outcomes
    default = effective_default(step, outcomes)
    partners: dict[str, Outcome] = {}
    for a, b in pairs:
        partners.setdefault(a.option.id, b)
        partners.setdefault(b.option.id, a)

    async def one(outcome: Outcome) -> Outcome:
        other = partners.get(outcome.option.id)
        if other is None:
            return outcome
        return await _rewrite(config, repair, parent, step, outcome, other, kind, summary, default)

    updated = list(await asyncio.gather(*(one(o) for o in outcomes)))
    remaining = find_pairs(kind, step, [o for o in updated if o.status != "failed"])
    _record_unresolved(config, kind, step, remaining)
    return updated


async def resolve_outputs(
    config: SmokeConfig,
    repair: Repair,
    parent: Checkpoint,
    step: Step,
    outcomes: list[Outcome],
    summary: CodingSummary | None,
) -> list[Outcome]:
    if config.rewrite is None:
        return outcomes
    outcomes = await _resolve(config, repair, parent, step, outcomes, summary, COLLISION)
    if step.kind == "model":
        outcomes = await _resolve(config, repair, parent, step, outcomes, summary, SCALE)
    return outcomes


async def resolve_extra(
    config: SmokeConfig,
    repair: Repair,
    parent: Checkpoint,
    step: Step,
    outcome: Outcome,
) -> Outcome:
    if config.rewrite is None:
        return outcome
    for kind in (COLLISION, SCALE):
        peers = [p for p in config.state.outcomes.get(step.id, []) if p.status != "failed"]
        other = next((p for p in peers if predicate(kind, step, outcome, p)), None)
        if other is None:
            continue
        outcome = await _rewrite(
            config,
            repair,
            parent,
            step,
            outcome,
            other,
            kind,
            None,
            config.state.defaults.get(step.id),
        )
        still = next((p for p in peers if predicate(kind, step, outcome, p)), None)
        if still is not None:
            _record_unresolved(config, kind, step, [(still, outcome)])
    return outcome


def remember_extra(config: SmokeConfig, step: Step, outcome: Outcome) -> None:
    config.state.outcomes.setdefault(step.id, []).append(outcome)
