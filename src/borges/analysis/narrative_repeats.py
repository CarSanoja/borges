from __future__ import annotations

import re

SENTENCE = re.compile(r"(?<=[.!?])\s+")
NUMBER = re.compile(r"-?\d+(?:\.\d+)?%?")
WORD = re.compile(r"[a-z]{3,}")
CONTENT = re.compile(r"[a-z]{4,}")
OVERLAP = 0.5
RESTATED = 0.6
MIN_SHARED = 4
QUOTED = re.compile(r"'([^']{3,})'")
STOP = frozenset({"that", "this", "with", "from", "were", "have", "been", "they", "their", "which"})


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
    for sentence in SENTENCE.split(narrative.strip()):
        if not any(_repeats(sentence, earlier) for earlier in kept):
            kept.append(sentence)
    return " ".join(kept)


def _content(text: str) -> set[str]:
    return {w.rstrip("s") for w in CONTENT.findall(text.lower().replace("-", " "))} - STOP


def restates_any(text: str, earlier: list[str]) -> bool:
    words, quoted = _content(text), QUOTED.findall(text)
    for other in earlier:
        if not all(q in other for q in quoted):
            continue
        before = _content(other)
        shared = len(words & before)
        if shared >= MIN_SHARED and shared / (min(len(words), len(before)) or 1) >= RESTATED:
            return True
    return False
