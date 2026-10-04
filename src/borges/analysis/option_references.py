from __future__ import annotations

import re

from borges.analysis.models import AnalysisPlan, Option, Step

MAX_REFERENCED_SPEC = 500
MIN_LABEL_CHARS = 4
CUE = re.compile(r"\b(same as|similar to|like|as in|as for|based on|plus|but)\b", re.IGNORECASE)


def _mentions(text: str, needle: str) -> bool:
    if not needle:
        return False
    return re.search(rf"(?<![\w]){re.escape(needle)}(?![\w])", text, re.IGNORECASE) is not None


def _words(text: str) -> str:
    return " ".join(re.sub(r"[\W_]+", " ", text).lower().split())


def _mentions_id(text: str, option_id: str) -> bool:
    """'OLS-HC3' names the option ols_hc3: compared as words, an id of two or more words."""
    words = _words(option_id)
    return " " in words and f" {words} " in f" {_words(text)} "


def _clip(spec: str) -> str:
    spec = " ".join(spec.split())
    return spec if len(spec) <= MAX_REFERENCED_SPEC else spec[: MAX_REFERENCED_SPEC - 3] + "..."


def _referenced(plan: AnalysisPlan, step: Step, option: Option) -> list[Option]:
    label_text = option.label if CUE.search(option.label) else ""
    text = f"{label_text} {option.spec}"
    id_text = f"{option.label} {option.spec}"
    found: list[Option] = []
    for other_step in plan.steps:
        for other in other_step.options:
            if other.id == option.id or other in found:
                continue
            by_id = _mentions(id_text, other.id)
            same_step = other_step.id == step.id
            by_label = (
                same_step and len(other.label) >= MIN_LABEL_CHARS and _mentions(text, other.label)
            )
            by_words = same_step and bool(CUE.search(id_text)) and _mentions_id(id_text, other.id)
            if by_id or by_label or by_words:
                found.append(other)
    return found


def expand_option(plan: AnalysisPlan, step: Step, option: Option) -> Option:
    spec = option.spec
    for other in _referenced(plan, step, option):
        marker = f"({other.id}:"
        if marker in spec:
            continue
        spec = f"{spec} {marker} {_clip(other.spec)})"
    return option if spec == option.spec else option.model_copy(update={"spec": spec})


def normalise_plan(plan: AnalysisPlan) -> AnalysisPlan:
    snapshot = plan.model_copy(deep=True)
    for step, original in zip(plan.steps, snapshot.steps, strict=True):
        step.options = [expand_option(snapshot, original, o) for o in original.options]
    return plan
