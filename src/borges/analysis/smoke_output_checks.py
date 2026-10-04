from __future__ import annotations

import math

from borges.analysis.models import Step
from borges.analysis.prompts.coder_collision import COLLISION
from borges.analysis.smoke_types import Outcome

REL_TOL = 1e-9
SCALE_GAP = 0.01
RESULT_KEYS = ("estimate", "ci_low", "ci_high", "p_value")


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=1e-12)


def _different_specs(a: Outcome, b: Outcome) -> bool:
    return " ".join(a.option.spec.split()) != " ".join(b.option.spec.split())


def same_output(step: Step, a: Outcome, b: Outcome) -> bool:
    if step.kind == "model":
        left, right = a.result, b.result
        if left is None or right is None or left["n"] != right["n"]:
            return False
        return all(_close(float(left[k]), float(right[k])) for k in RESULT_KEYS)
    left_fp = (a.effects or {}).get("fingerprint")
    right_fp = (b.effects or {}).get("fingerprint")
    return left_fp is not None and left_fp == right_fp


def scale_mismatch(step: Step, a: Outcome, b: Outcome) -> bool:
    if step.kind != "model" or a.result is None or b.result is None:
        return False
    left, right = a.result, b.result
    if left["n"] != right["n"] or not _close(float(left["p_value"]), float(right["p_value"])):
        return False
    gap = abs(float(left["estimate"]) - float(right["estimate"]))
    return gap > SCALE_GAP * max(abs(float(left["estimate"])), abs(float(right["estimate"])))


def predicate(kind: str, step: Step, a: Outcome, b: Outcome) -> bool:
    if not _different_specs(a, b):
        return False
    return same_output(step, a, b) if kind == COLLISION else scale_mismatch(step, a, b)


def find_pairs(kind: str, step: Step, live: list[Outcome]) -> list[tuple[Outcome, Outcome]]:
    return [
        (a, b) for i, a in enumerate(live) for b in live[i + 1 :] if predicate(kind, step, a, b)
    ]
