from __future__ import annotations

import re

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Change, Report

_TOKEN = re.compile(r"[a-z0-9]+")
_SUFFIXES = ("ing", "ed", "es", "s", "e")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_HOLE = "\0"


def _stem(word: str) -> str:
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def _tokens(text: str) -> list[str]:
    return [_stem(word) for word in _TOKEN.findall(text.lower())]


def _blank(tokens: list[str], label: list[str]) -> list[str]:
    out = list(tokens)
    for start in range(len(out) - len(label) + 1):
        if label and out[start : start + len(label)] == label:
            out[start : start + len(label)] = [_HOLE] * len(label)
    return out


def _mentions(tokens: list[str], label: list[str]) -> bool:
    return any(
        tokens[start : start + len(label)] == label for start in range(len(tokens) - len(label) + 1)
    )


def _from_label(plan: AnalysisPlan, change: Change) -> str:
    try:
        return plan.step(change.step_id).option(change.from_option).label
    except StopIteration:
        return change.from_option


def flip_sentence(plan: AnalysisPlan, report: Report) -> str | None:
    flip = report.minimal_flip
    if flip is None or not flip.changes:
        return None
    parts = [
        f'{change.step_title} from "{_from_label(plan, change)}" to "{change.to_label}"'
        for change in flip.changes
    ]
    return f"The minimal flip changes {' and '.join(parts)}."


def has_sentence(narrative: str, sentence: str) -> bool:
    return " ".join(sentence.split()) in " ".join(narrative.split())


def wrong_labels(plan: AnalysisPlan, report: Report, narrative: str) -> list[str]:
    flip = report.minimal_flip
    if flip is None:
        return []
    text = _tokens(narrative)
    found: list[str] = []
    for change in flip.changes:
        step = plan.step(change.step_id)
        for label in (_from_label(plan, change), change.to_label):
            text = _blank(text, _tokens(label))
        for option in step.options:
            label = _tokens(option.label)
            if option.id in (change.from_option, change.to_option) or len(label) < 2:
                continue
            if _mentions(text, label):
                found.append(option.label)
    return found


def problems(plan: AnalysisPlan, report: Report, narrative: str) -> list[str]:
    sentence = flip_sentence(plan, report)
    if sentence is None:
        return []
    found: list[str] = []
    if not has_sentence(narrative, sentence):
        found.append(f"the flip sentence is missing: {sentence}")
    found.extend(
        f'it names the option "{label}", which is not part of the minimal flip'
        for label in wrong_labels(plan, report, narrative)
    )
    return found


def insert_sentence(narrative: str, sentence: str) -> str:
    parts = _SENTENCE_END.split(narrative.strip(), maxsplit=1)
    if len(parts) == 1:
        return f"{parts[0]} {sentence}"
    return f"{parts[0]} {sentence} {parts[1]}"


def drop_wrong_sentences(plan: AnalysisPlan, report: Report, narrative: str) -> str:
    kept = [
        sentence
        for sentence in _SENTENCE_END.split(narrative.strip())
        if not wrong_labels(plan, report, sentence)
    ]
    return " ".join(kept)
