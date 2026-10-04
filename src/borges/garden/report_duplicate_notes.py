from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.garden.models import DuplicateOption, Flip, NoopOption


def dead_step_notes(plan: AnalysisPlan, noops: list[NoopOption]) -> list[str]:
    dead = {(n.step_id, n.option_id) for n in noops}
    notes: list[str] = []
    for step in plan.decision_steps:
        alternatives = [o for o in step.options if o.id != step.default.id]
        if not all((step.id, o.id) in dead for o in alternatives):
            continue
        what = "covariate decision" if step.kind == "feature" else "decision"
        notes.append(
            f"The {what} '{step.title}' had no effect on the model: every alternative gave the "
            "same result as the default, so the model ignores or always includes what this step "
            "changes. Its options are excluded from the robustness share, which must not be "
            "read as evidence of robustness to this decision."
        )
    return notes


def duplicate_notes(duplicates: list[DuplicateOption]) -> list[str]:
    return [
        f"The option '{d.label}' ({d.step_id}) duplicates '{d.kept_label}' "
        f"({d.kept_origin} option of the same step): {d.reason}. It is excluded from the "
        "robustness share and from the flip search, and counts as one path with the kept option."
        for d in duplicates
    ]


def flip_attribution_notes(flip: Flip | None, duplicates: list[DuplicateOption]) -> list[str]:
    if flip is None:
        return []
    notes: list[str] = []
    for change in flip.changes:
        for d in duplicates:
            if d.step_id == change.step_id and d.kept_option_id == change.to_option:
                notes.append(
                    f"The minimal flip's option '{change.to_label}' ({change.step_id}) is "
                    f"the {d.kept_origin} option's; '{d.label}' gives the same point estimate, "
                    "so it is one finding, not two independent ones."
                )
    return notes
