from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from borges.api.deps import get_registry
from borges.api.sse import sse_response
from borges.cases.models import CaseCard

if TYPE_CHECKING:
    from borges.cases.registry import CaseRegistry

router = APIRouter()
Registry = Annotated[Any, Depends(get_registry)]


def _card_or_404(registry: CaseRegistry, case_id: str) -> CaseCard:
    try:
        card = registry.card(case_id)
    except KeyError:
        card = None
    if card is None:
        raise HTTPException(status_code=404, detail=f"Unknown case '{case_id}'.")
    return card


@router.get("/cases")
def list_cases(registry: Registry) -> list[CaseCard]:
    return registry.list()


@router.get("/cases/{case_id}")
def get_case(case_id: str, registry: Registry) -> CaseCard:
    return _card_or_404(registry, case_id)


@router.get("/cases/{case_id}/recording")
def case_recording(
    case_id: str,
    registry: Registry,
    speed: Annotated[float, Query(gt=0, le=100)] = 4.0,
    source: Annotated[Literal["live", "scripted"] | None, Query()] = None,
):
    card = _card_or_404(registry, case_id)
    chosen = source or ("live" if card.live_recording else "scripted")
    events = registry.recording(case_id, chosen)
    if not events:
        raise HTTPException(
            status_code=404, detail=f"Case '{case_id}' has no {chosen} recorded run."
        )
    from borges.runs.replay import replay_events

    return sse_response(replay_events(events, speed))
