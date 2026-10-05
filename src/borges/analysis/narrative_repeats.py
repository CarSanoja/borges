from __future__ import annotations

import re

SENTENCE = re.compile(r"(?<=[.!?])\s+")
NUMBER = re.compile(r"-?\d+(?:\.\d+)?%?")
WORD = re.compile(r"[a-z]{3,}")
OVERLAP = 0.5
SAME_WORDS = 0.85
RESTATED_OPENING = re.compile(r"([^()]{1,60}) \(\1 \(")
REEXECUTION = re.compile(r"\bre-?execut\w*|\breproduc\w*", re.IGNORECASE)
SHORT = 16


def _numbers(sentence: str) -> list[str]:
    return sorted(NUMBER.findall(sentence))


def _words(sentence: str) -> set[str]:
    return set(WORD.findall(sentence.lower()))


def _repeats(sentence: str, earlier: str) -> bool:
    """Same figures and half the words, or no figures and nearly all the words: the hurricanes
    summary at 2327203 said twice that one filter decision had no effect."""
    numbers = _numbers(sentence)
    if numbers != _numbers(earlier):
        return False
    words, before = _words(sentence), _words(earlier)
    shorter = min(len(words), len(before)) or 1
    return len(words & before) / shorter >= (OVERLAP if numbers else SAME_WORDS)


def drop_repeated_sentences(narrative: str) -> str:
    kept: list[str] = []
    narrative = RESTATED_OPENING.sub(r"\1 (", narrative)
    for sentence in SENTENCE.split(narrative.strip()):
        if not any(_repeats(sentence, earlier) for earlier in kept) and not _restated_reproduction(
            sentence, kept
        ):
            kept.append(sentence)
    return " ".join(kept)


def _restated_reproduction(sentence: str, kept: list[str]) -> bool:
    """A marp_norms summary at 9b95d04 said the flip was reproduced twice, in other words."""
    if not REEXECUTION.search(sentence) or _numbers(sentence) or len(sentence.split()) > SHORT:
        return False
    return any(REEXECUTION.search(earlier) for earlier in kept)


def drop_prompt_echoes(narrative: str, rules: tuple[str, ...], labels: tuple[str, ...] = ()) -> str:
    """A model told to copy a sentence sometimes copies the instruction next to it as well, or
    the label the prompt put before it."""
    kept = []
    for sentence in SENTENCE.split(narrative.strip()):
        if sentence.strip() in rules:
            continue
        for label in labels:
            if sentence.startswith(label):
                sentence = sentence[len(label)].upper() + sentence[len(label) + 1 :]
        kept.append(sentence)
    return " ".join(kept)
