from __future__ import annotations

import logging

from borges.config import Settings

log = logging.getLogger("borges.memory")


class ApprovalCheck:
    """Whether the agent version that wrote a memory is the approved version in force.

    A clinic rerun after coder 2.65.0 (r_20261009T070254_637cec) reused the model code that coder
    2.64.0 had written for the same option, so the template fix that the new version carried never
    ran: an older version stays approved after a newer one is published. A memory now counts only
    when the latest approved version of its agent wrote it.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._store = None
        self._cache: dict[tuple[str, str], bool] = {}

    def approved(self, agent_id: str | None, definition_sha: str | None) -> bool:
        if agent_id is None:
            return True
        if definition_sha is None:
            return False
        key = (agent_id, definition_sha)
        if key not in self._cache:
            self._cache[key] = self._lookup(agent_id, definition_sha)
        return self._cache[key]

    def _lookup(self, agent_id: str, definition_sha: str) -> bool:
        try:
            if self._store is None:
                from borges.fleet.locations import open_store

                self._store = open_store(self.settings)
            approved = [r for r in self._store.versions_of(agent_id) if r.state == "approved"]
        except Exception:
            log.warning("registry unavailable: memories are ignored", exc_info=True)
            return False
        return bool(approved) and approved[-1].definition_sha == definition_sha
