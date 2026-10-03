from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pydantic import RootModel

from borges.llm.json_output import parse_model

LABELLED = re.compile(r"([AB])\s*(\d+)", re.IGNORECASE)
BARE = re.compile(r"\d+")


class MatchTable(RootModel[dict[str, Any]]):
    pass


@dataclass(frozen=True)
class MatchPair:
    expert: int
    agent: int
    similarity: int


def _sides(key: str) -> tuple[list[int], list[int]] | None:
    labelled = [(m.group(1).upper(), int(m.group(2))) for m in LABELLED.finditer(key)]
    expert = [n for letter, n in labelled if letter == "A"]
    agent = [n for letter, n in labelled if letter == "B"]
    if expert and agent:
        return expert, agent
    numbers = BARE.findall(key)
    if not labelled and len(numbers) == 2:
        return [int(numbers[0])], [int(numbers[1])]
    return None


def _similarity(value: dict) -> int | None:
    raw = value.get("similarity", 10)
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def parse_pairs(text: str, n_expert: int, n_agent: int, offset: int = 0) -> list[MatchPair]:
    table = parse_model(text, MatchTable).root
    pairs: list[MatchPair] = []
    seen: set[tuple[int, int]] = set()
    for key, value in table.items():
        sides = _sides(key)
        if sides is None or not isinstance(value, dict):
            continue
        similarity = _similarity(value)
        if similarity is None:
            continue
        for left in sides[0]:
            for right in sides[1]:
                cell = (left - 1, right - 1)
                if 0 <= cell[0] < n_expert and 0 <= cell[1] < n_agent and cell not in seen:
                    seen.add(cell)
                    pairs.append(MatchPair(cell[0], cell[1] + offset, similarity))
    return pairs
