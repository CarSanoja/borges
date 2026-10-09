from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache

from borges.armor.findings import Finding, clip
from borges.armor.normalize import normalize_identifier, variants_of
from borges.armor.patterns_code import CODE, CODE_STEERING
from borges.armor.patterns_goal import EXFIL, STEERING
from borges.armor.patterns_instruction import COMPOSED_OVERRIDE, OVERRIDE, ROLE
from borges.armor.patterns_semantic import SEMANTIC

Patterns = tuple[tuple[str, str], ...]

TEXT_PATTERNS: Patterns = (*OVERRIDE, *ROLE, *STEERING, *EXFIL, *CODE)
MODEL_OUTPUT_PATTERNS: Patterns = (*TEXT_PATTERNS, *CODE_STEERING)
MAX_SCREEN_CHARS = 20000
WINDOW_OVERLAP = 400
MAX_TOTAL_CHARS = 1_000_000
OVERSIZE = "input.oversize"


@dataclass(frozen=True)
class ScreenProfile:
    name: str
    patterns: Patterns


UNTRUSTED_INPUT = ScreenProfile("untrusted_input", (*TEXT_PATTERNS, *SEMANTIC))
MODEL_OUTPUT = ScreenProfile("model_output", MODEL_OUTPUT_PATTERNS)
PROMPT_INPUT = ScreenProfile("prompt_input", (*COMPOSED_OVERRIDE, *ROLE, *STEERING, *EXFIL))
CODE_OUTPUT = ScreenProfile("code_output", (*COMPOSED_OVERRIDE, *ROLE, *EXFIL, *CODE))


@cache
def _compiled(profile: ScreenProfile) -> tuple[tuple[str, re.Pattern[str]], ...]:
    return tuple(
        (name, re.compile(pattern, re.IGNORECASE | re.DOTALL)) for name, pattern in profile.patterns
    )


def _windows(text: str) -> Iterable[str]:
    step = MAX_SCREEN_CHARS - WINDOW_OVERLAP
    for start in range(0, min(len(text), MAX_TOTAL_CHARS), step):
        yield text[start : start + MAX_SCREEN_CHARS]


def _scan(window: str, profile: ScreenProfile, found: dict[tuple[str, str], Finding]) -> None:
    for variant in variants_of(window):
        for name, pattern in _compiled(profile):
            match = pattern.search(variant.text)
            if match is None or (name, variant.technique) in found or (name, "plain") in found:
                continue
            found[(name, variant.technique)] = Finding(
                category=name,
                pattern=name,
                technique=variant.technique,
                quote=clip(match.group(0)),
            )


def screen_text(text: str, profile: ScreenProfile = UNTRUSTED_INPUT) -> list[Finding]:
    """Screen the original text and every normalised variant; return the distinct findings."""
    if not text or not text.strip():
        return []
    found: dict[tuple[str, str], Finding] = {}
    for window in _windows(text):
        _scan(window, profile, found)
    if len(text) > MAX_TOTAL_CHARS:
        found[(OVERSIZE, "plain")] = Finding(
            OVERSIZE, OVERSIZE, "plain", f"{len(text)} characters exceed the screening limit"
        )
    return list(found.values())


def screen_identifier(value: str, profile: ScreenProfile = UNTRUSTED_INPUT) -> list[Finding]:
    findings = screen_text(value, profile)
    if findings:
        return findings
    return screen_text(normalize_identifier(value), profile)


def screen_many(texts: Iterable[str], profile: ScreenProfile = UNTRUSTED_INPUT) -> list[Finding]:
    return screen_text("\n".join(texts), profile)
