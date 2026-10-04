from __future__ import annotations

from borges.analysis.models import CodingSummary, Step
from borges.analysis.smoke_collision import resolve_extra
from borges.analysis.smoke_core import smoke_option
from borges.analysis.smoke_larger import smoke_rows
from borges.analysis.smoke_model_input import Fault
from borges.analysis.smoke_review import _re_review
from borges.analysis.smoke_types import Outcome, Repair, SmokeConfig
from borges.analysis.smoke_upstream import _short, probe_option
from borges.llm.client import LLMError

MODEL_REPAIR_MESSAGE = (
    "This model option fails on the sample with:\n{error}\n"
    "It fails when the earlier step '{title}' uses the option '{label}' ({spec}) while it "
    "works on the default path. The code must work for every option of the earlier steps, "
    "for example by reading ctx lists as lists and building the design without string formulas."
)
MODEL_DROPPED_NOTE = (
    "The model option '{label}' was dropped: with the option '{upstream}' of the step "
    "'{title}' it fails on the sample ({error})."
)
MODEL_CAUGHT_NOTE = "caught under '{upstream}': {error}"


async def _repaired_model(
    config: SmokeConfig,
    repair: Repair,
    model: Step,
    outcome: Outcome,
    failures: list[Fault],
) -> Outcome | None:
    item, upstream, error = failures[0]
    message = MODEL_REPAIR_MESSAGE.format(
        error=error,
        title=upstream.title,
        label=item.outcome.option.label,
        spec=item.outcome.option.spec,
    )
    try:
        code, violation, name = await repair(model, outcome.option, message, outcome.attempts)
    except LLMError:
        return None
    if violation is not None:
        return None
    parent = config.state.parents[model.id]
    option = outcome.option.model_copy(update={"code": code})
    tried = await smoke_option(config, repair, parent, model, option, budget=0)
    if tried.status != "failed":
        tried = await _re_review(config, model, tried)
    if tried.status != "failed":
        tried = await resolve_extra(config, repair, parent, model, tried)
    if tried.status == "failed":
        return None
    for failed_item, _, _ in failures:
        if await probe_option(config, repair, model, tried.option, failed_item.checkpoint):
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


async def _handle_model(
    config: SmokeConfig,
    repair: Repair,
    model: Step,
    outcome: Outcome,
    failures: list[Fault],
    summary: CodingSummary | None,
) -> None:
    item, upstream, error = failures[0]
    label = item.outcome.option.label
    fresh = await _repaired_model(config, repair, model, outcome, failures)
    outcomes = config.state.outcomes[model.id]
    option_id = outcome.option.id
    if fresh is not None:
        model.options = [fresh.option if o.id == option_id else o for o in model.options]
        config.state.outcomes[model.id] = [
            fresh if o.option.id == option_id else o for o in outcomes
        ]
        if summary is not None:
            summary.repaired_after_smoke += 1
        if config.on_smoke is not None:
            await config.on_smoke(
                model.id,
                option_id,
                "repaired",
                fresh.attempts,
                MODEL_CAUGHT_NOTE.format(upstream=label, error=_short(error)),
                fresh.models,
                *smoke_rows(fresh),
            )
        return
    model.options = [o for o in model.options if o.id != option_id]
    config.state.outcomes[model.id] = [o for o in outcomes if o.option.id != option_id]
    note = MODEL_DROPPED_NOTE.format(
        label=outcome.option.label, upstream=label, title=upstream.title, error=_short(error)
    )
    config.state.notes.append(note)
    if summary is not None:
        summary.failed += 1
    if config.on_smoke is not None:
        await config.on_smoke(model.id, option_id, "failed", outcome.attempts, note, outcome.models)


async def handle_model(
    config: SmokeConfig,
    repair: Repair,
    model: Step,
    outcome: Outcome,
    failures: list[Fault],
    summary: CodingSummary | None,
) -> None:
    item, upstream, error = failures[0]
    label = item.outcome.option.label
    fresh = await _repaired_model(config, repair, model, outcome, failures)
    outcomes = config.state.outcomes[model.id]
    option_id = outcome.option.id
    if fresh is not None:
        model.options = [fresh.option if o.id == option_id else o for o in model.options]
        config.state.outcomes[model.id] = [
            fresh if o.option.id == option_id else o for o in outcomes
        ]
        if summary is not None:
            summary.repaired_after_smoke += 1
        if config.on_smoke is not None:
            await config.on_smoke(
                model.id,
                option_id,
                "repaired",
                fresh.attempts,
                MODEL_CAUGHT_NOTE.format(upstream=label, error=_short(error)),
                fresh.models,
                *smoke_rows(fresh),
            )
        return
    model.options = [o for o in model.options if o.id != option_id]
    config.state.outcomes[model.id] = [o for o in outcomes if o.option.id != option_id]
    note = MODEL_DROPPED_NOTE.format(
        label=outcome.option.label, upstream=label, title=upstream.title, error=_short(error)
    )
    config.state.notes.append(note)
    if summary is not None:
        summary.failed += 1
    if config.on_smoke is not None:
        await config.on_smoke(model.id, option_id, "failed", outcome.attempts, note, outcome.models)
