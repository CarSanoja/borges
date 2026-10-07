"""The user's own option of a step, dropped in coding, brought back by the reference repair.

fertility_vote on 7 October, run 18: the coder twice read ctx['next_onset'] as a date instead of
a column name, so the step's default, the user's own cycle day, failed its smoke run and an
alternative (days since the last period) became the default. Two independent implementations of
the analysis agreed on the published cell, but the repair could only correct the options left
in the plan, and the starting point stayed a changed analysis. The dropped option is now offered
to the repairer with its last error; a fix for it puts it back as the step's default.
"""

from __future__ import annotations

from dataclasses import dataclass

from borges.analysis.coder_smoke import FAILED_NOTE
from borges.analysis.models import AnalysisPlan, Option
from borges.analysis.smoke_types import Outcome
from borges.runs.pipeline_caveats import DEPARTURE

ERROR_CHARS = 600


@dataclass
class Lost:
    step_id: str
    option: Option
    error: str | None


def lost_defaults(
    planned: AnalysisPlan | None, plan: AnalysisPlan, outcomes: dict[str, list[Outcome]]
) -> dict[tuple[str, str], Lost]:
    if planned is None:
        return {}
    found: dict[tuple[str, str], Lost] = {}
    for step in planned.steps:
        now = next((s for s in plan.steps if s.id == step.id), None)
        if not step.options or now is None or not now.options:
            continue
        original = step.default
        if any(o.id == original.id for o in now.options):
            continue
        tried = [o for o in outcomes.get(step.id, []) if o.option.id == original.id]
        error = tried[-1].error if tried else None
        found[(step.id, original.id)] = Lost(
            step.id, original, error[:ERROR_CHARS] if error else None
        )
    return found


def restore(plan: AnalysisPlan, lost: Lost, code: str, spec: str | None) -> None:
    step = plan.step(lost.step_id)
    for option in step.options:
        option.is_default = False
    back = lost.option.model_copy(
        deep=True, update={"code": code, "spec": spec or lost.option.spec, "is_default": True}
    )
    step.options = [back, *step.options]


def withdraw_departures(caveats: list[str], plan: AnalysisPlan, restored: list[Lost]) -> None:
    """The caveats that said the step's own option could not run no longer hold."""
    stale: list[str] = []
    for lost in restored:
        title = plan.step(lost.step_id).title
        stale.append(DEPARTURE.format(title=title))
        stale.append(FAILED_NOTE.split("(")[0].format(label=lost.option.label, title=title))
    caveats[:] = [c for c in caveats if not any(c.startswith(s) for s in stale)]
