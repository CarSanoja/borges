from __future__ import annotations

from borges.analysis.covariate_ids import listed_identifiers
from borges.analysis.models import DatasetProfile
from borges.analysis.profile_flags import flagged_columns
from borges.analysis.schemas import PlannedStep

MIN_BRANCHING_STEPS = 3
PRODUCING_KINDS = ("transform", "feature")


def _step_text(step: PlannedStep) -> str:
    parts = [step.title, step.description]
    parts.extend(f"{o.label} {o.rationale} {o.spec}" for o in step.options)
    return " ".join(parts).lower()


def plan_shortfalls(steps: list[PlannedStep], profile: DatasetProfile) -> list[str]:
    problems: list[str] = []
    if not any(s.kind == "model" for s in steps):
        problems.append(
            "No step has kind 'model'. The last step must be the model step "
            '(kind "model") that estimates the effect and returns estimate, ci_low, '
            "ci_high and p_value."
        )
    models = [s.id for s in steps if s.kind == "model"]
    if len(models) > 1:
        problems.append(
            "Only one step may have kind 'model'; merge these into one final model step whose "
            f"options are the alternative model families: {', '.join(models)}."
        )
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
    missing = [s.id for s in steps if s.kind in PRODUCING_KINDS and not s.produces]
    if missing:
        problems.append(
            "These transform or feature steps do not declare produces; list the exact new "
            "column names or ctx keys that every option of the step creates, under the same "
            f"name and meaning: {', '.join(missing)}."
        )
    listed = sorted(
        {name for s in steps for o in s.options for name in listed_identifiers(o.spec, profile)}
    )
    if listed:
        problems.append(
            f"These identifier columns appear in a covariate list: {', '.join(listed)}. An "
            "identifier with many distinct values is no covariate (as dummies the design is too "
            "wide to fit, as a number its coding is arbitrary); leave it out of every covariate "
            "list, and cluster the standard errors on it in the model step where that is needed."
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
