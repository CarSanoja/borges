from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from borges.api.deps import get_settings
from borges.api.live_rules import (
    live_unavailable_reason,
    read_spend,
    uploads_unavailable_reason,
)
from borges.config import Settings

router = APIRouter()


@router.get("/health")
def health(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, Any]:
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
    }
