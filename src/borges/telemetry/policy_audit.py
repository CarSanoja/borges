from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException

from borges.config import Settings
from borges.telemetry.audit_log import AuditLog
from borges.telemetry.run_telemetry import global_audit_path

REASON_CHARS = 300


def audit_global(settings: Settings, kind: str, **fields: Any) -> None:
    AuditLog(global_audit_path(settings)).append(kind, **fields)


def audited_policy[T](
    settings: Settings, name: str, check: Callable[..., T], *args: Any, **data: Any
) -> T:
    try:
        result = check(*args)
    except HTTPException as exc:
        audit_global(
            settings,
            f"policy.{name}",
            decision="deny",
            reason=str(exc.detail)[:REASON_CHARS],
            data={"status": exc.status_code, **data},
        )
        raise
    audit_global(settings, f"policy.{name}", decision="allow", data=data)
    return result
