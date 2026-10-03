from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from borges.bench.blade_matcher import MatcherUsage, MatchPair

MINI = Path(__file__).parent / "fixtures" / "blade_mini"

RULES = {
    "cvar": [("hurricane name", "femininity"), ("intensity", "pressure"), ("year", "year")],
    "model": [("negative binomial", "negative binomial"), ("linear regression", "linear model")],
    "transform": [("remove hurricane katrina", "drop")],
}


@dataclass
class FakeMatcher:
    name: str = "fake"
    usage: MatcherUsage = field(default_factory=MatcherUsage)
    seen: list[str] = field(default_factory=list)

    async def match(
        self, kind: str, question: str, schema: str, expert: list[str], agent: list[str]
    ) -> list[MatchPair]:
        self.seen.append(kind)
        self.usage.calls += 1
        self.usage.cost_usd += 0.001
        pairs = []
        for needle_e, needle_a in RULES.get(kind, []):
            for i, left in enumerate(expert):
                for j, right in enumerate(agent):
                    if needle_e in left.lower() and needle_a in right.lower():
                        pairs.append(MatchPair(i, j, 9))
        return pairs
