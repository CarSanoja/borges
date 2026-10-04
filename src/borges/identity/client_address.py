from __future__ import annotations

import ipaddress

from starlette.requests import Request

from borges.config import Settings

FORWARDED_FOR = "x-forwarded-for"


def _valid(candidate: str) -> str | None:
    try:
        return str(ipaddress.ip_address(candidate.strip()))
    except ValueError:
        return None


def client_address(request: Request, settings: Settings) -> str:
    peer = request.client.host if request.client else "unknown"
    if not settings.borges_trusted_proxy:
        return peer
    chain = [part for part in request.headers.get(FORWARDED_FOR, "").split(",") if part.strip()]
    hops = max(1, settings.borges_trusted_proxy_hops)
    if len(chain) < hops:
        return peer
    return _valid(chain[-hops]) or peer
