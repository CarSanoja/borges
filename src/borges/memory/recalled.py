from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from borges.memory.entry import MemoryEntry

Match = Literal["exact", "family", "similar"]


@dataclass(frozen=True)
class Recalled:
    entry: MemoryEntry
    match: Match
    score: float = 1.0

    @property
    def payload(self) -> dict:
        return self.entry.payload

    @property
    def run_id(self) -> str:
        return self.entry.run_id
