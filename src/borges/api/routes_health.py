from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from borges.api.deps import get_settings
from borges.config import Settings

router = APIRouter()


def read_spend(settings: Settings) -> float:
    path = settings.borges_home / "spend.json"
    try:
        raw: Any = json.loads(path.read_text())
    except (OSError, ValueError):
        return 0.0
    if isinstance(raw, dict):
        raw = raw.get("total_usd", raw.get("spend_usd", 0.0))
    return float(raw) if isinstance(raw, (int, float)) else 0.0


@router.get("/health")
def health(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, Any]:
    return {
        "status": "ok",
        "llm": settings.borges_llm,
        "llm_live_available": bool(settings.nebius_api_key),
        "backend": settings.borges_backend,
        "spend_usd": read_spend(settings),
        "spend_cap_usd": settings.borges_spend_cap_usd,
    }
