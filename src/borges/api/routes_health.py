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
from borges.identity.client_address import client_address
from borges.identity.deps import get_principal
from borges.identity.principal import Principal

router = APIRouter()


@router.get("/health")
def health(
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
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
        "est_cost_per_live_run_usd": settings.borges_typical_run_cost_usd,
        "max_cost_per_live_run_usd": settings.borges_run_cap_usd,
        "anon_live_quota": _anon_quota(request, settings, principal),
        **_capacity(request),
    }


def _anon_quota(request: Request, settings: Settings, principal: Principal) -> dict[str, Any]:
    quota = request.app.state.anon_live_quota
    view = quota.view(client_address(request, settings)).as_dict()
    return {"applies": principal.anonymous, **view}


IDLE = {
    "queue_depth": 0,
    "active_workers": 0,
    "oldest_job_age_s": None,
    "dead_letter_count": 0,
}


def _capacity(request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    return runtime.stats() if runtime is not None else dict(IDLE)
