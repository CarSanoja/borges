from __future__ import annotations

import json
import re
from pathlib import Path

from borges.cases.registry import CaseRegistry

ROOT = Path(__file__).resolve().parents[2]
FALLBACK = ROOT / "frontend" / "src" / "features" / "cases" / "fallbackCases.ts"


def _fallback_blocks() -> dict[str, str]:
    text = FALLBACK.read_text()
    blocks = re.split(r"\n  \{\n", text)[1:]
    return {re.search(r'id: "([^"]+)"', block).group(1): block for block in blocks}


def _string_field(block: str, name: str) -> str:
    match = re.search(rf"\b{name}: (\"(?:[^\"\\\\]|\\\\.)*\")", block)
    assert match, name
    return json.loads(match.group(1))


def test_fallback_cards_match_the_curated_cases() -> None:
    blocks = _fallback_blocks()
    cards = CaseRegistry(ROOT / "cases").list()
    assert sorted(blocks) == sorted(card.id for card in cards)
    for card in cards:
        block = blocks[card.id]
        assert _string_field(block, "title") == card.title
        assert _string_field(block, "question") == card.question
        assert _string_field(block, "positive_label") == card.decision_rule.positive_label
        assert _string_field(block, "provenance") == card.provenance
        assert _string_field(block, "negative_label") == card.decision_rule.negative_label
        assert re.search(rf"\bn_rows: {card.n_rows},", block), card.id
        assert ("live_only: true" in block) == card.live_only, card.id
