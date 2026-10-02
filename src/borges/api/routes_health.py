from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from borges.api.deps import get_settings
from borges.api.live_rules import (
    live_unavailable_reason,
    read_spend,
    uploads_unavailable_reason,
)
from borges.config import Settings

router = APIRouter()


@router.get("/health")
def health(
    settings: Annotated[Settings, Depends(get_settings)], request: Request
) -> dict[str, Any]:
    spend = read_spend(settings)
    reason = live_unavailable_reason(settings)
    uploads_reason = uploads_unavailable_reason(settings)
    return {
        "status": "ok",
        "llm": settings.borges_llm,
        "llm_live_available": reason is None,
        "live_unavailable_reason": reason,
        "uploads_available": uploads_reason is None,
        "uploads_unavailable_reason": uploads_reason,
        "backend": settings.borges_backend,
        "spend_usd": spend,
        "spend_cap_usd": settings.borges_spend_cap_usd,
        **_capacity(request),
    }


IDLE = {
    "queue_depth": 0,
    "active_workers": 0,
    "oldest_job_age_s": None,
    "dead_letter_count": 0,
}


def _capacity(request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    return runtime.stats() if runtime is not None else dict(IDLE)
