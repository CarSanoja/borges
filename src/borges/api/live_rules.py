from __future__ import annotations

import json
from typing import Any, Literal

from borges.config import Settings

LiveReason = Literal["no_key", "budget_spent", "bare_host"]

UNTRUSTED_LOCAL_MESSAGE = (
    "Uploaded datasets run live only on isolated sandboxes (BORGES_BACKEND=contree), "
    "or with BORGES_ALLOW_UNTRUSTED_LOCAL=true on a private machine."
)
BARE_HOST_MESSAGE = (
    "A live run executes code a model wrote, and this server would run it on its own host. Live "
    "runs need isolated sandboxes (BORGES_BACKEND=contree), a server inside a container "
    "(BORGES_ISOLATED_HOST=true, set by the Docker image), or BORGES_ALLOW_UNTRUSTED_LOCAL=true "
    "on a private machine."
)
UPLOAD_LIVE_MESSAGES: dict[LiveReason, str] = {
    "no_key": "Uploaded datasets run live and this server has no NEBIUS_API_KEY.",
    "budget_spent": "Uploaded datasets run live and the live budget of this demo is used up.",
    "bare_host": BARE_HOST_MESSAGE,
}


def read_spend(settings: Settings) -> float:
    path = settings.borges_home / "spend.json"
    try:
        raw: Any = json.loads(path.read_text())
    except (OSError, ValueError):
        return 0.0
    if isinstance(raw, dict):
        raw = raw.get("total_usd", raw.get("spend_usd", 0.0))
    return float(raw) if isinstance(raw, (int, float)) else 0.0


def live_unavailable_reason(settings: Settings) -> LiveReason | None:
    if not settings.nebius_api_key:
        return "no_key"
    if read_spend(settings) >= settings.borges_spend_cap_usd:
        return "budget_spent"
    if bare_host(settings):
        return "bare_host"
    return None


def bare_host(settings: Settings) -> bool:
    """Model-written code would run on the server's own host, outside any container."""
    return (
        settings.borges_backend == "local"
        and not settings.borges_isolated_host
        and not settings.borges_allow_untrusted_local
    )


def untrusted_local_blocked(settings: Settings) -> bool:
    return settings.borges_backend == "local" and not settings.borges_allow_untrusted_local


def uploads_unavailable_reason(settings: Settings) -> str | None:
    live = live_unavailable_reason(settings)
    if live is not None:
        return UPLOAD_LIVE_MESSAGES[live]
    if untrusted_local_blocked(settings):
        return UNTRUSTED_LOCAL_MESSAGE
    return None
