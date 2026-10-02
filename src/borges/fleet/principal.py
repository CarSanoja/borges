from __future__ import annotations

PRINCIPAL_PREFIX = "agent://borges/"


def agent_principal(agent_id: str) -> str:
    return f"{PRINCIPAL_PREFIX}{agent_id}"


def agent_id_of(principal: str) -> str | None:
    if principal.startswith(PRINCIPAL_PREFIX):
        return principal[len(PRINCIPAL_PREFIX) :] or None
    return None
