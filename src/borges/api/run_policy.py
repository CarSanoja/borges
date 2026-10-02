from __future__ import annotations

import hmac
from typing import Any

from fastapi import HTTPException

from borges.api.live_rules import (
    UNTRUSTED_LOCAL_MESSAGE,
    read_spend,
    untrusted_local_blocked,
    uploads_unavailable_reason,
)
from borges.config import Settings
from borges.runs.models import RunRequest

LIVE_TOKEN_HEADER = "X-Borges-Live-Token"


def _reject(status: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail=detail)


def _check_live(
    request: RunRequest, settings: Settings, orchestrator: Any, live_token: str | None
) -> None:
    if not settings.nebius_api_key:
        raise _reject(
            400,
            "Live runs need NEBIUS_API_KEY. Set it in .env, or request "
            "llm=scripted for the offline demo.",
        )
    if read_spend(settings) >= settings.borges_spend_cap_usd:
        raise _reject(403, "The live budget for this demo is used up; watch the recorded run.")
    if request.upload_id is None:
        if request.question or request.decision_rule is not None:
            raise _reject(
                400, "Live runs on a curated case use its own question and decision rule."
            )
    else:
        _check_upload_trust(settings, live_token)
    if orchestrator.live_count() >= settings.borges_max_live_runs:
        raise _reject(
            429,
            f"At most {settings.borges_max_live_runs} live runs can run at once. Try again soon.",
        )


def _check_upload_trust(settings: Settings, live_token: str | None) -> None:
    if untrusted_local_blocked(settings):
        raise _reject(400, UNTRUSTED_LOCAL_MESSAGE)
    expected = settings.borges_live_token
    if expected and not hmac.compare_digest(
        (live_token or "").encode("utf-8"), expected.encode("utf-8")
    ):
        raise _reject(403, "Uploaded datasets need a valid live token.")


def enforce_upload_policy(settings: Settings, live_token: str | None) -> None:
    if untrusted_local_blocked(settings):
        raise _reject(403, UNTRUSTED_LOCAL_MESSAGE)
    reason = uploads_unavailable_reason(settings)
    if reason is not None:
        raise _reject(403, reason)
    _check_upload_trust(settings, live_token)


def enforce_run_policy(
    request: RunRequest, settings: Settings, orchestrator: Any, live_token: str | None
) -> RunRequest:
    if request.backend is not None and request.backend != settings.borges_backend:
        raise _reject(
            400,
            f"This server runs the {settings.borges_backend} backend; "
            "the server chooses the backend.",
        )
    ceiling = settings.borges_max_universes
    clamped = min(request.max_universes or ceiling, ceiling)
    request = request.model_copy(update={"max_universes": clamped})
    if orchestrator.active_count() >= settings.borges_max_active_runs:
        raise _reject(
            429,
            "Borges is busy with other runs; watch the recorded run or try again in a minute.",
        )
    llm = request.llm or settings.borges_llm
    if request.upload_id is not None and llm != "nebius":
        raise _reject(400, "Uploaded datasets need live mode (llm=nebius with NEBIUS_API_KEY).")
    if llm == "nebius":
        _check_live(request, settings, orchestrator, live_token)
    return request
