from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence

from borges.runs.events import Event

PREPARATION = frozenset(
    {"option.coded", "option.smoke", "option.reviewed", "step.replanned", "usage"}
)


async def replay_events(
    events: Sequence[Event],
    speed: float = 1.0,
    max_gap_s: float = 1.5,
    preparation_gap_s: float = 0.15,
) -> AsyncIterator[Event]:
    """Re-emit stored events, spaced by their original timestamp gaps divided by `speed`."""
    if speed <= 0:
        raise ValueError("speed must be positive")
    previous_ts: float | None = None
    for event in events:
        if previous_ts is not None:
            cap = preparation_gap_s if event.type in PREPARATION else max_gap_s
            gap = min(max((event.ts - previous_ts) / speed, 0.0), cap)
            await asyncio.sleep(gap)
        previous_ts = event.ts
        yield event
