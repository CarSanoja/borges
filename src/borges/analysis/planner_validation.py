from __future__ import annotations

from borges.analysis.models import DatasetProfile
from borges.analysis.profile_flags import flagged_columns
from borges.analysis.schemas import PlannedStep

MIN_BRANCHING_STEPS = 3


def _step_text(step: PlannedStep) -> str:
    parts = [step.title, step.description]
    parts.extend(f"{o.label} {o.rationale} {o.spec}" for o in step.options)
    return " ".join(parts).lower()


def plan_shortfalls(steps: list[PlannedStep], profile: DatasetProfile) -> list[str]:
    problems: list[str] = []
    single = [s.id for s in steps if len(s.options) < 2]
    if single:
        problems.append(
            "These steps have a single option; give each at least two defensible options "
            f"(or drop the step if it is not a judgement call): {', '.join(single)}."
        )
    branching = len(steps) - len(single)
    if branching < MIN_BRANCHING_STEPS:
        problems.append(
            f"Only {branching} steps have two or more options; at least "
            f"{MIN_BRANCHING_STEPS} are required."
        )
    flags, outliers = flagged_columns(profile)
    names = [c.name for c in flags + outliers]
    text = " ".join(_step_text(s) for s in steps)
    if names and not any(n.lower() in text for n in names):
        problems.append(
            "The profile shows columns that may mark records to exclude or extreme values "
            f"({', '.join(names)}), but no step decides whether to keep or exclude them; add a "
            "data-inclusion step whose options keep and exclude those records."
        )
    return problems
