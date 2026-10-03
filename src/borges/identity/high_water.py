from __future__ import annotations

from pathlib import Path
from typing import Any

from borges.identity.chain_links import ChainBroken


class HighWater:
    """The longest chain this process has seen: a shorter or different one means a rollback."""

    def __init__(self) -> None:
        self.count = 0
        self.head: str | None = None

    def check(self, path: Path, events: list[dict[str, Any]]) -> None:
        if len(events) < self.count:
            raise ChainBroken(
                path,
                len(events) + 1,
                f"the store has {len(events)} records but this process already saw "
                f"{self.count}: it was rolled back while running",
            )
        if self.count and events[self.count - 1].get("hash") != self.head:
            raise ChainBroken(
                path,
                self.count,
                f"record {self.count} is not the one this process saw: the store was "
                "replaced while running",
            )
        if len(events) > self.count:
            self.count, self.head = len(events), events[-1].get("hash")
