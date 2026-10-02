from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from borges.cases.models import LiveRecordingSummary
from borges.runs.events import Event
from borges.runs.state import fold

RecordingSource = Literal["scripted", "live"]
LIVE_FOLDER = "recorded-live"


def _recorded_at(events: list[Event]) -> str:
    started = next((e for e in events if e.type == "run.started"), events[0])
    stamp = datetime.fromtimestamp(started.ts, tz=UTC)
    return stamp.isoformat(timespec="seconds").replace("+00:00", "Z")


def _models(events: list[Event]) -> dict[str, str]:
    started = next((e for e in events if e.type == "run.started"), None)
    raw = started.data.get("models") if started else None
    return {str(k): str(v) for k, v in raw.items()} if isinstance(raw, dict) else {}


def summarize_live(events: list[Event]) -> LiveRecordingSummary:
    snapshot = fold(events, events[0].run_id)
    garden = snapshot.garden
    baseline = garden.universes.get(garden.baseline_id) if garden.baseline_id else None
    flip = snapshot.flip
    verdict = flip.baseline_verdict if flip else (baseline.verdict if baseline else None)
    usage = snapshot.usage
    return LiveRecordingSummary(
        recorded_at=_recorded_at(events),
        models=_models(events),
        llm_calls=usage.llm_calls,
        tokens_in=usage.tokens_in,
        tokens_out=usage.tokens_out,
        cost_usd=usage.cost_usd,
        verdict=verdict,
        flipped_verdict=flip.flipped_verdict if flip else None,
        flip_kind=flip.kind if flip else None,
        universes=usage.universes or len(garden.universes),
    )
