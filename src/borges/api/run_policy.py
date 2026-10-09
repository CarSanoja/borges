from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

from borges.api.live_rules import (
    BARE_HOST_MESSAGE,
    UNTRUSTED_LOCAL_MESSAGE,
    bare_host,
    read_spend,
    untrusted_local_blocked,
    uploads_unavailable_reason,
)
from borges.config import Settings
from borges.fleet.enforcement import USER_MESSAGE, RegistryBlocked, enforce_registry
from borges.runs.models import RunRequest
from borges.telemetry.policy_audit import audit_global

logger = logging.getLogger(__name__)


def _reject(status: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail=detail)


def _busy_message(request: RunRequest, active: int) -> str:
    base = f"Borges is already running {active} analyses, the most this server allows;"
    if request.upload_id is None:
        return f"{base} watch the recorded run or try again in a minute."
    return f"{base} try again in a minute."


def validate_run_request(request: RunRequest) -> None:
    if request.upload_id is None:
        return
    rule = request.decision_rule
    missing = []
    if not request.question or not request.question.strip():
        missing.append("a question")
    if rule is None:
        missing.append("a decision_rule")
    if rule is None or missing:
        raise _reject(
            400,
            "Uploaded datasets need both a question and a decision_rule; "
            f"missing {' and '.join(missing)}.",
        )
    problems = rule.problems()
    if problems:
        raise _reject(400, f"The decision rule is not valid: {'; '.join(problems)}.")


def _check_live(request: RunRequest, settings: Settings, orchestrator: Any) -> None:
    if not settings.nebius_api_key:
        raise _reject(
            400,
            "Live runs need NEBIUS_API_KEY. Set it in .env, or request "
            "llm=scripted for the offline demo.",
        )
    if read_spend(settings) >= settings.borges_spend_cap_usd:
        raise _reject(403, "The live budget for this demo is used up; watch the recorded run.")
    if bare_host(settings):
        raise _reject(400, BARE_HOST_MESSAGE)
    if request.upload_id is None:
        if request.question or request.decision_rule is not None:
            raise _reject(
                400, "Live runs on a curated case use its own question and decision rule."
            )
    elif untrusted_local_blocked(settings):
        raise _reject(400, UNTRUSTED_LOCAL_MESSAGE)
    if orchestrator.live_count() >= settings.borges_max_live_runs:
        raise _reject(
            429,
            f"At most {settings.borges_max_live_runs} live runs can run at once. Try again soon.",
        )


def _check_registry(settings: Settings, llm: str) -> None:
    try:
        enforce_registry(settings, llm)
    except RegistryBlocked as blocked:
        logger.warning("live run refused by the agent registry: %s", blocked)
        audit_global(
            settings,
            "policy.registry_blocked",
            decision="deny",
            reason=str(blocked),
            data={"blockers": [b.model_dump() for b in blocked.blockers]},
        )
        raise _reject(409, USER_MESSAGE) from blocked


def enforce_upload_policy(settings: Settings) -> None:
    if untrusted_local_blocked(settings):
        raise _reject(403, UNTRUSTED_LOCAL_MESSAGE)
    reason = uploads_unavailable_reason(settings)
    if reason is not None:
        raise _reject(403, reason)


def enforce_run_policy(request: RunRequest, settings: Settings, orchestrator: Any) -> RunRequest:
    if request.backend is not None and request.backend != settings.borges_backend:
        raise _reject(
            400,
            f"This server runs the {settings.borges_backend} backend; "
            "the server chooses the backend.",
        )
    if request.llm == "local":
        raise _reject(
            400,
            "llm=local is CLI only (Nemotron 3 Nano on Ollama, on the operator's machine); "
            "the server pins its own mode.",
        )
    ceiling = settings.borges_max_universes
    clamped = min(request.max_universes or ceiling, ceiling)
    request = request.model_copy(update={"max_universes": clamped})
    active = orchestrator.active_count()
    if active >= settings.borges_max_active_runs:
        raise _reject(429, _busy_message(request, active))
    llm = request.llm or settings.borges_llm
    if request.upload_id is not None and llm != "nebius":
        raise _reject(400, "Uploaded datasets need live mode (llm=nebius with NEBIUS_API_KEY).")
    if llm == "nebius":
        _check_live(request, settings, orchestrator)
        _check_registry(settings, llm)
    return request
