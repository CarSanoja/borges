from __future__ import annotations

from fastapi import HTTPException, Request

from borges.identity.principal import ANONYMOUS, Principal
from borges.identity.route_table import scope_label


def get_principal(request: Request) -> Principal:
    found = request.scope.get("state", {}).get("principal")
    return found if isinstance(found, Principal) else ANONYMOUS


def require_scope(principal: Principal, *scopes: str) -> None:
    if principal.has_any(scopes):
        return
    who = "Anonymous demo access" if principal.anonymous else principal.id
    hint = " Paste an API key with this scope in the header." if principal.anonymous else ""
    raise HTTPException(
        status_code=403,
        detail=f"{who} lacks the required scope: {scope_label(scopes)}.{hint}",
    )
