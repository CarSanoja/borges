from __future__ import annotations

from collections.abc import Awaitable, Callable

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Universe

MAX_RECOVERIES = 2
ERROR_LIMIT = 160
RunBaseline = Callable[[dict[str, str]], Awaitable[Universe]]


def failing_option(plan: AnalysisPlan, error: str | None) -> tuple[str, str] | None:
    head = (error or "").split(":", 1)[0].strip()
    step_id, _, option_id = head.partition("/")
    step = next((s for s in plan.steps if s.id == step_id), None)
    if step is None or not any(o.id == option_id for o in step.options):
        return None
    if step.default.id != option_id or len(step.options) < 2:
        return None
    return step_id, option_id


def demote(plan: AnalysisPlan, step_id: str, option_id: str, error: str) -> str:
    step = plan.step(step_id)
    failed = step.option(option_id)
    step.options = [o for o in step.options if o.id != option_id]
    for option in step.options:
        option.is_default = False
    promoted = step.options[0]
    promoted.is_default = True
    reason = " ".join(error.split(":", 1)[-1].split())[:ERROR_LIMIT]
    return (
        f"The default option '{failed.label}' of the step '{step.title}' failed on the full data "
        f"({reason}); '{promoted.label}' was promoted to default and the baseline re-run, and the "
        "original default is left out of the analysis."
    )


async def recover_baseline(
    plan: AnalysisPlan, baseline: Universe, run: RunBaseline, caveats: list[str]
) -> Universe:
    for _ in range(MAX_RECOVERIES):
        if baseline.status == "done":
            return baseline
        target = failing_option(plan, baseline.error)
        if target is None:
            break
        caveats.append(demote(plan, *target, baseline.error or ""))
        baseline = await run(plan.default_choices())
    if baseline.status != "done":
        raise RuntimeError(f"the baseline analysis failed: {baseline.error}")
    return baseline
