from __future__ import annotations

import re

from borges.analysis.covariate_ids import listed_identifiers
from borges.analysis.models import DatasetProfile, DecisionRule
from borges.analysis.planner_measure import linear_odds_shortfall
from borges.analysis.planner_products import renamed_products, renamed_shortfall
from borges.analysis.profile_flags import flagged_columns
from borges.analysis.schemas import PlannedStep
from borges.analysis.shadow_columns import shadow_copies, shadow_shortfall

MIN_BRANCHING_STEPS = 3
RESULT_NAMES = {"estimate", "ci_low", "ci_high", "p_value"}
RESULT_TEXT = re.compile(r"\b(?:ci_low|ci_high|p_value)\b|\bmodel(?:'s)? (?:output|results?)\b")
PRODUCING_KINDS = ("transform", "feature")


def _step_text(step: PlannedStep) -> str:
    parts = [step.title, step.description]
    parts.extend(f"{o.label} {o.rationale} {o.spec}" for o in step.options)
    return " ".join(parts).lower()


def reads_the_result(steps: list[PlannedStep]) -> list[str]:
    """Steps placed after the model step that read or format what the model returns."""
    first = next((i for i, s in enumerate(steps) if s.kind == "model"), len(steps))
    late = [s for s in steps[first + 1 :] if s.kind != "model"]
    return [
        s.id
        for s in late
        if RESULT_NAMES & set(s.produces) or RESULT_TEXT.search(_step_text(s)) is not None
    ]


def plan_shortfalls(
    steps: list[PlannedStep], profile: DatasetProfile, rule: DecisionRule | None = None
) -> list[str]:
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
    late = reads_the_result(steps)
    if late:
        problems.append(
            "These steps come after the model step, which is the last step and returns the "
            "result itself (estimate, ci_low, ci_high, p_value); no step can read or format its "
            f"output, so remove them: {', '.join(late)}."
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
    linear = linear_odds_shortfall(steps, rule)
    if linear is not None:
        problems.append(linear)
    renamed = renamed_shortfall(renamed_products(steps, profile), steps)
    if renamed is not None:
        problems.append(renamed)
    columns = {c.name for c in profile.columns}
    shadows = {
        f"{s.id}.{o.id}": found
        for s in steps
        if s.kind != "model"
        for o in s.options
        if (found := shadow_copies(o.spec, s.produces, columns))
    }
    shadow = shadow_shortfall(shadows)
    if shadow is not None:
        problems.append(shadow)
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
