from __future__ import annotations

from collections.abc import Awaitable, Callable

from borges.analysis.models import Step
from borges.analysis.smoke_types import Outcome, Replan, Replanned, SmokeConfig
from borges.llm.client import LLMError
from borges.telemetry import hooks

SmokeRound = Callable[[], Awaitable[list[Outcome]]]
REASON_CHARS = 300


def has_survivor(outcomes: list[Outcome]) -> bool:
    return any(o.status != "failed" for o in outcomes)


def _last_error(outcomes: list[Outcome]) -> str:
    default = next((o for o in outcomes if o.error), None)
    last = next((o.error for o in reversed(outcomes) if o.error), None)
    return ((default.error if default else None) or last or "not coded")[:REASON_CHARS]


def _round(outcomes: list[Outcome], coding: dict[str, str]) -> str:
    tried = ", ".join([*(o.option.id for o in outcomes), *coding]) or "none"
    errors = [f"{k}: {v}" for k, v in coding.items()]
    last = _last_error(outcomes) if outcomes else (errors[-1] if errors else "not coded")
    return f"options tried: {tried}; last error: {last}"


def both_rounds_message(
    step: Step, first: list[Outcome], second: list[Outcome], replanned: Replanned
) -> str:
    return (
        f"step {step.id}: no option passed its smoke run, and the planner's one re-plan of the "
        f"step also failed. First round: {_round(first, {})}. "
        f"Re-plan: {_round(second, replanned.errors)}"
    )


async def replan_outcomes(
    config: SmokeConfig,
    replan: Replan,
    step: Step,
    first: list[Outcome],
    smoke_again: SmokeRound,
) -> list[Outcome]:
    with hooks.span("step.replan", f"step.replan {step.id}", **{"borges.step_id": step.id}) as span:
        replanned = await replan(step, first)
        if replanned is None:
            span.set_attribute("borges.step.replanned", False)
            return first
        failed_ids = [o.option.id for o in first]
        new_ids = [o.id for o in replanned.options]
        span.set_attribute("borges.step.replanned", True)
        span.set_attribute("borges.step.failed_options", failed_ids)
        span.set_attribute("borges.step.new_options", new_ids)
        if config.on_replan is not None:
            await config.on_replan(step.id, failed_ids, new_ids)
        proposed = ", ".join(new_ids) or "none that could be coded"
        config.state.notes.append(
            f"Every option of step {step.id} failed its smoke run ({', '.join(failed_ids)}); the "
            f"planner proposed replacements once: {proposed}."
        )
        step.options = replanned.options
        second = await smoke_again() if replanned.options else []
        if not has_survivor(second):
            raise LLMError(both_rounds_message(step, first, second, replanned))
        return second
