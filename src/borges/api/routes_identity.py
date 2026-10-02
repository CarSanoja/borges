from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request

from borges.api.deps import get_settings
from borges.config import Settings
from borges.identity.deps import get_principal
from borges.identity.principal import Principal
from borges.identity.rate_limit import RateLimiter
from borges.telemetry.audit_global_verify import verify_global
from borges.telemetry.audit_verify import read_records
from borges.telemetry.run_telemetry import global_audit_path

router = APIRouter()

PrincipalDep = Annotated[Principal, Depends(get_principal)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _client(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/me")
def me(request: Request, principal: PrincipalDep) -> dict[str, Any]:
    limiter: RateLimiter = request.app.state.limiter
    state = limiter.peek(principal, _client(request))
    return {
        "principal": principal.id,
        "kind": principal.kind,
        "anonymous": principal.anonymous,
        "scopes": sorted(principal.scopes),
        "key_id": principal.key_id,
        "expires_at": principal.expires_at,
        "rate_limit": {
            "limit": state.limit,
            "remaining": state.remaining,
            "refill_per_s": state.refill_per_s,
        },
    }


@router.get("/audit")
def global_audit(
    settings: SettingsDep,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    kind: Annotated[str | None, Query()] = None,
    principal: Annotated[str | None, Query()] = None,
    decision: Annotated[str | None, Query()] = None,
    verify: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    path = global_audit_path(settings)
    records = read_records(path)
    selected = [
        r
        for r in records
        if (kind is None or r.kind == kind)
        and (principal is None or r.principal == principal)
        and (decision is None or r.decision == decision)
    ]
    body: dict[str, Any] = {
        "total": len(records),
        "records": [r.model_dump(mode="json") for r in selected[-limit:]],
    }
    if verify:
        body["chain"] = verify_global(path, settings.borges_audit_anchor_key)
    return body
