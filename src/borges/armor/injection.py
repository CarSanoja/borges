from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache

from borges.armor.findings import Finding, clip
from borges.armor.normalize import normalize_identifier, variants_of
from borges.armor.patterns_code import CODE, CODE_STEERING
from borges.armor.patterns_goal import EXFIL, STEERING
from borges.armor.patterns_instruction import OVERRIDE, ROLE

Patterns = tuple[tuple[str, str], ...]

TEXT_PATTERNS: Patterns = (*OVERRIDE, *ROLE, *STEERING, *EXFIL, *CODE)
MODEL_OUTPUT_PATTERNS: Patterns = (*TEXT_PATTERNS, *CODE_STEERING)
MAX_SCREEN_CHARS = 20000


@dataclass(frozen=True)
class ScreenProfile:
    name: str
    patterns: Patterns


UNTRUSTED_INPUT = ScreenProfile("untrusted_input", TEXT_PATTERNS)
MODEL_OUTPUT = ScreenProfile("model_output", MODEL_OUTPUT_PATTERNS)
PROMPT_INPUT = ScreenProfile("prompt_input", (*OVERRIDE, *ROLE, *STEERING, *EXFIL))
CODE_OUTPUT = ScreenProfile("code_output", (*OVERRIDE, *ROLE, *EXFIL, *CODE))


@cache
def _compiled(profile: ScreenProfile) -> tuple[tuple[str, re.Pattern[str]], ...]:
    return tuple(
        (name, re.compile(pattern, re.IGNORECASE | re.DOTALL)) for name, pattern in profile.patterns
    )


def screen_text(text: str, profile: ScreenProfile = UNTRUSTED_INPUT) -> list[Finding]:
    """Screen the original text and every normalised variant; return the distinct findings."""
    if not text or not text.strip():
        return []
    sample = text[:MAX_SCREEN_CHARS]
    found: dict[tuple[str, str], Finding] = {}
    for variant in variants_of(sample):
        for name, pattern in _compiled(profile):
            match = pattern.search(variant.text)
            if match is None:
                continue
            key = (name, variant.technique)
            if key not in found:
                found[key] = Finding(
                    category=name,
                    pattern=name,
                    technique=variant.technique,
                    quote=clip(match.group(0)),
                )
    return list(found.values())


def screen_identifier(value: str, profile: ScreenProfile = UNTRUSTED_INPUT) -> list[Finding]:
    findings = screen_text(value, profile)
    if findings:
        return findings
    return screen_text(normalize_identifier(value), profile)


def screen_many(texts: Iterable[str], profile: ScreenProfile = UNTRUSTED_INPUT) -> list[Finding]:
    return screen_text("\n".join(texts), profile)
