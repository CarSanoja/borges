from __future__ import annotations

import re

SENTENCE = re.compile(r"(?<=[.!?])\s+")
NUMBER = re.compile(r"-?\d+(?:\.\d+)?%?")
WORD = re.compile(r"[a-z]{3,}")
OVERLAP = 0.5
RESTATED_OPENING = re.compile(r"([^()]{1,60}) \(\1 \(")


def _numbers(sentence: str) -> list[str]:
    return sorted(NUMBER.findall(sentence))


def _words(sentence: str) -> set[str]:
    return set(WORD.findall(sentence.lower()))


def _repeats(sentence: str, earlier: str) -> bool:
    numbers = _numbers(sentence)
    if not numbers or numbers != _numbers(earlier):
        return False
    words, before = _words(sentence), _words(earlier)
    shorter = min(len(words), len(before)) or 1
    return len(words & before) / shorter >= OVERLAP


def drop_repeated_sentences(narrative: str) -> str:
    kept: list[str] = []
    narrative = RESTATED_OPENING.sub(r"\1 (", narrative)
    for sentence in SENTENCE.split(narrative.strip()):
        if not any(_repeats(sentence, earlier) for earlier in kept):
            kept.append(sentence)
    return " ".join(kept)


def drop_prompt_echoes(narrative: str, rules: tuple[str, ...]) -> str:
    """A model told to copy a sentence sometimes copies the instruction next to it as well."""
    kept = [s for s in SENTENCE.split(narrative.strip()) if s.strip() not in rules]
    return " ".join(kept)
