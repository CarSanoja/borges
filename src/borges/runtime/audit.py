from __future__ import annotations

import logging
from typing import Any

from borges.config import Settings
from borges.telemetry.policy_audit import audit_global

log = logging.getLogger("borges.runtime")


def record(settings: Settings, kind: str, **fields: Any) -> None:
    try:
        audit_global(settings, kind, **fields)
    except Exception:
        log.warning("could not audit %s", kind, exc_info=True)
