from __future__ import annotations

import logging

from borges.config import Settings

log = logging.getLogger("borges.memory")


class ApprovalCheck:
    """Whether the agent version that wrote a memory is still approved in the registry."""

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
            record = self._store.by_definition(agent_id, definition_sha)
        except Exception:
            log.warning("registry unavailable: memories are ignored", exc_info=True)
            return False
        return record is not None and record.state == "approved"
