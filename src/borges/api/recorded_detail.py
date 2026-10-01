from __future__ import annotations

from typing import Any

from borges.runs.detail import build_universe_detail
from borges.runs.models import UniverseDetail
from borges.runs.state import fold


def recorded_universe_detail(registry: Any, run_id: str, universe_id: str) -> UniverseDetail:
    for card in registry.list():
        events = registry.recording(card.id) or []
        if events and events[0].run_id == run_id:
            return build_universe_detail(fold(events, run_id), universe_id)
    raise KeyError(run_id)
