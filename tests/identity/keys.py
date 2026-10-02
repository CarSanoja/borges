from __future__ import annotations

from borges.config import Settings
from borges.identity.keystore import open_keystore


def make_key(
    settings: Settings,
    scopes: str = "uploads:write,runs:create:live:upload",
    name: str = "tester",
    ttl_s: float | None = None,
) -> str:
    _, token = open_keystore(settings).create(name, scopes, ttl_s)
    return token


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
