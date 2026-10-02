from __future__ import annotations

import logging

from borges.config import Settings
from borges.identity.run_identity import RunIdentity, mint_run_identity

log = logging.getLogger("borges.runs")


def mint_identity(settings: Settings, run_id: str) -> RunIdentity | None:
    try:
        return mint_run_identity(settings, run_id)
    except Exception:
        log.warning(
            "agent tokens unavailable for this run", extra={"run_id": run_id}, exc_info=True
        )
        return None
