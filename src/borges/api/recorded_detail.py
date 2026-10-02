from __future__ import annotations

from typing import Any

from borges.runs.models import RunSnapshot
from borges.runs.state import fold


def recorded_case_id(registry: Any, run_id: str) -> str | None:
    for card in registry.list():
        if not card.has_recording:
            continue
        events = registry.recording(card.id) or []
        if events and events[0].run_id == run_id:
            return card.id
    return None


def recorded_snapshot(registry: Any, run_id: str) -> RunSnapshot:
    case_id = recorded_case_id(registry, run_id)
    if case_id is None:
        raise KeyError(run_id)
    return fold(registry.recording(case_id) or [], run_id)
