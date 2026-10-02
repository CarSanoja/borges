from __future__ import annotations

from starlette.types import Scope

from borges.identity.principal import Principal
from borges.identity.route_table import OPEN, RouteRequirement, scope_label
from borges.identity.scopes import PUBLIC_SCOPES

DUPLICATE_AUTHORIZATION = "duplicate authorization headers"


def client_of(scope: Scope) -> str:
    client = scope.get("client")
    return str(client[0]) if client else "unknown"


def headers_of(scope: Scope) -> dict[str, str]:
    headers: dict[str, str] = {}
    for raw_key, raw_value in scope["headers"]:
        key = raw_key.decode("latin-1").lower()
        if key == "authorization" and key in headers:
            headers[key] = DUPLICATE_AUTHORIZATION
            continue
        headers[key] = raw_value.decode("latin-1")
    return headers


def is_public(requirement: RouteRequirement | None) -> bool:
    if requirement is None or requirement == OPEN:
        return True
    scopes = {requirement} if isinstance(requirement, str) else set(requirement)
    return scopes <= PUBLIC_SCOPES


def permits(principal: Principal, requirement: RouteRequirement) -> bool:
    if isinstance(requirement, str):
        return principal.has(requirement)
    return principal.has_any(requirement)


def forbidden_message(principal: Principal, requirement: RouteRequirement) -> str:
    who = "Anonymous demo access" if principal.anonymous else principal.id
    hint = " Paste an API key with this scope in the header." if principal.anonymous else ""
    return f"{who} lacks the required scope: {scope_label(requirement)}.{hint}"
