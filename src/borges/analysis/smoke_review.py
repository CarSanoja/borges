from __future__ import annotations

import asyncio
from typing import Any

from borges.analysis.models import AnalysisPlan, CodingSummary, Step
from borges.analysis.prompts.reviewer import build_messages
from borges.analysis.review_dummies import apply_contracts
from borges.analysis.schemas import ReviewerOutput, ReviewVerdict
from borges.analysis.smoke_core import smoke_option
from borges.analysis.smoke_orientation import (
    effective_default,
    notify_changed,
    orientation_error,
    produced_names,
)
from borges.analysis.smoke_types import (
    Outcome,
    Repair,
    ReviewEntry,
    Reviewer,
    ReviewResult,
    SmokeConfig,
)
from borges.llm.client import LLMClient, LLMError, Role
from borges.sandbox.backend import Checkpoint

CHANGES_ESTIMAND = "the reviewer found that this option changes the estimand: {problem}"
STILL_UNFAITHFUL = "the repaired code is still unfaithful to its spec on re-review: {problem}"
NOT_RE_REVIEWED = "the repaired code could not be re-reviewed, so it cannot enter the garden"


def _slim_effects(effects: dict[str, Any] | None) -> dict[str, Any] | None:
    if not effects:
        return None
    slim = {k: v for k, v in effects.items() if k not in ("columns", "fingerprint")}
    columns = effects.get("columns") or {}
    slim["columns"] = {
        name: {k: v for k, v in stats.items() if k != "probe"} for name, stats in columns.items()
    }
    return slim


def _payload(entry: ReviewEntry) -> dict[str, Any]:
    option = entry.option
    payload: dict[str, Any] = {
        "option_id": option.id,
        "label": option.label,
        "spec": option.spec,
        "code": option.code,
        "effects": _slim_effects(entry.effects),
    }
    if entry.result is not None:
        payload["smoke_result"] = entry.result
    return payload


def llm_reviewer(llm: LLMClient, plan: AnalysisPlan) -> Reviewer:
    async def review(
        step: Step, entries: list[ReviewEntry], again: bool = False
    ) -> ReviewResult | None:
        try:
            response = await llm.complete(
                Role.REVIEWER,
                build_messages(plan, step, [_payload(e) for e in entries]),
                key=f"reviewer:{step.id}:again" if again else f"reviewer:{step.id}",
                schema=ReviewerOutput,
                max_tokens=1500,
            )
        except LLMError:
            return None
        out = ReviewerOutput.model_validate(response.parsed)
        notes = {e.option.id: (e.effects or {}).get("harness_note") for e in entries}
        verdicts = apply_contracts(out.verdicts, notes, plan.decision_rule)
        return ReviewResult(verdicts, response.usage.model)

    return review


async def _handle(
    config: SmokeConfig,
    repair: Repair,
    parent: Checkpoint,
    step: Step,
    default: Outcome,
    outcome: Outcome,
    verdict: ReviewVerdict,
) -> Outcome:
    if verdict.changes_estimand:
        error = CHANGES_ESTIMAND.format(problem=verdict.problem)
        return Outcome(outcome.option, "failed", outcome.attempts, error, None, outcome.models)
    names = produced_names(step.produces, default.effects)

    def check(effects: dict[str, Any] | None) -> str | None:
        if outcome is default or not names:
            return None
        return orientation_error(names, default.effects, effects)

    problem = verdict.problem or "the code does not do what the spec says"
    resume = (outcome.attempts, outcome.models, problem)
    return await smoke_option(
        config, repair, parent, step, outcome.option, check, resume=resume, budget=1
    )


async def _re_review(config: SmokeConfig, step: Step, repaired: Outcome) -> Outcome:
    if repaired.status == "failed" or config.reviewer is None:
        return repaired
    entry = ReviewEntry(repaired.option, repaired.effects, repaired.result)
    result = await config.reviewer(step, [entry], again=True)
    verdict = next(
        (v for v in (result.verdicts if result else []) if v.option_id == repaired.option.id),
        None,
    )
    if result is not None and verdict is not None and config.on_review is not None:
        await config.on_review(
            step.id,
            repaired.option.id,
            verdict.faithful,
            verdict.changes_estimand,
            verdict.problem,
            result.model,
        )
    if verdict is not None and verdict.faithful and not verdict.changes_estimand:
        return repaired
    error = (
        NOT_RE_REVIEWED
        if verdict is None
        else STILL_UNFAITHFUL.format(problem=verdict.problem or "no reason given")
    )
    return Outcome(
        repaired.option, "failed", repaired.attempts, error, None, repaired.models, errors=[error]
    )


async def review_step(
    config: SmokeConfig,
    repair: Repair,
    parent: Checkpoint,
    step: Step,
    outcomes: list[Outcome],
    summary: CodingSummary | None,
) -> list[Outcome]:
    default = effective_default(step, outcomes)
    live = [o for o in outcomes if o.status != "failed"]
    if config.reviewer is None or default is None:
        return outcomes
    result = await config.reviewer(step, [ReviewEntry(o.option, o.effects, o.result) for o in live])
    if result is None:
        return outcomes
    if summary is not None:
        summary.steps_reviewed += 1
    verdicts = {v.option_id: v for v in result.verdicts}

    async def one(outcome: Outcome) -> Outcome:
        verdict = verdicts.get(outcome.option.id)
        if verdict is None or outcome.status == "failed":
            return outcome
        if config.on_review is not None:
            await config.on_review(
                step.id,
                outcome.option.id,
                verdict.faithful,
                verdict.changes_estimand,
                verdict.problem,
                result.model,
            )
        if verdict.faithful and not verdict.changes_estimand:
            return outcome
        updated = await _handle(config, repair, parent, step, default, outcome, verdict)
        updated = await _re_review(config, step, updated)
        if summary is not None:
            summary.options_flagged += 1
            summary.options_dropped_by_review += int(updated.status == "failed")
        await notify_changed(config, None, step, outcome, updated)
        return updated

    return list(await asyncio.gather(*(one(o) for o in outcomes)))


async def review_extra(
    config: SmokeConfig,
    repair: Repair,
    parent: Checkpoint,
    step: Step,
    default: Outcome,
    outcome: Outcome,
) -> Outcome:
    if config.reviewer is None:
        return outcome
    result = await config.reviewer(
        step, [ReviewEntry(outcome.option, outcome.effects, outcome.result)]
    )
    verdict = next(
        (v for v in (result.verdicts if result else []) if v.option_id == outcome.option.id), None
    )
    if result is None or verdict is None:
        return outcome
    if config.on_review is not None:
        await config.on_review(
            step.id,
            outcome.option.id,
            verdict.faithful,
            verdict.changes_estimand,
            verdict.problem,
            result.model,
        )
    if verdict.faithful and not verdict.changes_estimand:
        return outcome
    updated = await _handle(config, repair, parent, step, default, outcome, verdict)
    updated = await _re_review(config, step, updated)
    await notify_changed(config, None, step, outcome, updated)
    return updated
