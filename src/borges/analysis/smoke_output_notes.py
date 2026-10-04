from __future__ import annotations

from borges.analysis.models import Step
from borges.analysis.prompts.coder_collision import COLLISION
from borges.analysis.smoke_types import Outcome


def unresolved_note(kind: str, step: Step, a: Outcome, b: Outcome, metric: str) -> str:
    names = (
        f"{step.id}.{a.option.id} ({a.option.label}) and {step.id}.{b.option.id} ({b.option.label})"
    )
    if kind == COLLISION:
        return (
            f"Options {names} have different specs but produced identical output on the smoke "
            "sample even after one re-code, so one of them may not implement its own spec."
        )
    return (
        f"Options {names} give the same p-value and n but estimates on different scales "
        f"({_estimate(a)} vs {_estimate(b)}) even after one re-code; comparing them against the "
        f"decision rule metric ({metric}) may be misleading."
    )


def _estimate(outcome: Outcome) -> str:
    return f"{float((outcome.result or {})['estimate']):.4g}"


def applied_note(kind: str, target: Outcome, other: Outcome) -> str:
    if kind == COLLISION:
        return (
            f"caught an output collision with {other.option.id}: the code produced the same "
            "output although the specs differ; re-coded to implement its own spec"
        )
    return (
        f"caught a scale mismatch with {other.option.id}: same fit, same p-value, different "
        "scale; re-coded to report on the decision rule metric's scale"
    )
