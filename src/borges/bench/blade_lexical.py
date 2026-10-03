from __future__ import annotations

import re
from dataclasses import dataclass, field

from borges.bench.blade_matcher import MatcherUsage, MatchPair

TOKEN = re.compile(r"[a-z0-9]+")
STOP = frozenset(
    {
        "the",
        "a",
        "an",
        "of",
        "to",
        "in",
        "and",
        "or",
        "for",
        "with",
        "by",
        "on",
        "is",
        "as",
        "at",
        "be",
        "are",
        "from",
        "that",
        "this",
        "it",
        "its",
    }
)
MIN_OVERLAP = 0.45


def tokens(text: str) -> set[str]:
    return {t for t in TOKEN.findall(text.lower()) if t not in STOP and len(t) > 1}


@dataclass
class LexicalMatcher:
    """Token-overlap stand-in for the LLM matcher. It checks the plumbing, not BLADE scores."""

    threshold: float = MIN_OVERLAP
    name: str = "lexical-overlap (plumbing check, not a BLADE score)"
    usage: MatcherUsage = field(default_factory=MatcherUsage)

    async def match(
        self, kind: str, question: str, schema: str, expert: list[str], agent: list[str]
    ) -> list[MatchPair]:
        self.usage.calls += 1
        pairs: list[MatchPair] = []
        for i, left in enumerate(expert):
            a = tokens(left)
            for j, right in enumerate(agent):
                b = tokens(right)
                if not a or not b:
                    continue
                score = len(a & b) / min(len(a), len(b))
                if score >= self.threshold:
                    pairs.append(MatchPair(i, j, 8 + round(2 * min(score, 1.0)) - 1))
        return pairs
