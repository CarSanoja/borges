from __future__ import annotations

from pathlib import Path
from typing import Any

from borges.runs.models import RunSnapshot
from borges.runs.state import fold

SOURCES = ("live", "scripted")


def recorded_origin(registry: Any, run_id: str) -> tuple[str, str] | None:
    for card in registry.list():
        for source in SOURCES:
            available = (
                card.live_recording is not None if source == "live" else card.has_scripted_recording
            )
            if not available:
                continue
            events = registry.recording(card.id, source) or []
            if events and events[0].run_id == run_id:
                return card.id, source
    return None


def recorded_dir(registry: Any, run_id: str) -> Path | None:
    origin = recorded_origin(registry, run_id)
    locate = getattr(registry, "recording_dir", None)
    if origin is None or locate is None:
        return None
    return locate(*origin)


def recorded_snapshot(registry: Any, run_id: str) -> RunSnapshot:
    origin = recorded_origin(registry, run_id)
    if origin is None:
        raise KeyError(run_id)
    case_id, source = origin
    return fold(registry.recording(case_id, source) or [], run_id)
