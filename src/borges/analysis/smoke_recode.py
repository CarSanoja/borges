from __future__ import annotations

from borges.analysis.models import Step
from borges.analysis.smoke_core import smoke_option
from borges.analysis.smoke_types import Outcome, Recode, Repair, SmokeConfig
from borges.llm.client import LLMError
from borges.sandbox.backend import Checkpoint


async def _announce(config: SmokeConfig, step: Step, outcome: Outcome) -> None:
    if config.on_smoke is not None:
        await config.on_smoke(
            step.id,
            outcome.option.id,
            outcome.status,
            outcome.attempts,
            outcome.error,
            outcome.models,
        )


async def recode_failed_default(
    config: SmokeConfig,
    repair: Repair,
    recode: Recode | None,
    parent: Checkpoint,
    step: Step,
    outcomes: list[Outcome],
) -> list[Outcome]:
    failed = next(
        (o for o in outcomes if o.option.id == step.default.id and o.status == "failed"), None
    )
    if recode is None or failed is None:
        return outcomes
    errors = list(failed.errors) or ([failed.error] if failed.error else [])
    try:
        code, violation, model = await recode(step, failed.option, errors)
    except LLMError as exc:
        failed.errors = [*errors, f"fresh re-code unavailable: {exc}"]
        return outcomes
    fresh_option = failed.option.model_copy(update={"code": code})
    if violation is not None:
        fresh = Outcome(
            fresh_option,
            "failed",
            failed.attempts + 1,
            violation,
            None,
            [*failed.models, model],
            errors=[*errors, violation],
        )
    else:
        tried = await smoke_option(config, repair, parent, step, fresh_option, budget=0)
        fresh = Outcome(
            tried.option,
            "repaired" if tried.status == "passed" else "failed",
            failed.attempts + 1,
            tried.error,
            tried.checkpoint,
            [*failed.models, model],
            tried.effects,
            tried.result,
            [*errors, *tried.errors],
        )
    await _announce(config, step, fresh)
    return [fresh if o is failed else o for o in outcomes]
