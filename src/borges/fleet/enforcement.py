from __future__ import annotations

from pydantic import BaseModel

from borges.config import Settings
from borges.fleet.fleet import Fleet, build_fleet
from borges.fleet.locations import open_store
from borges.fleet.store import RegistryStore


class Blocker(BaseModel):
    agent_id: str
    definition_sha: str
    reason: str


class RegistryBlocked(RuntimeError):
    def __init__(self, blockers: list[Blocker]) -> None:
        self.blockers = blockers
        names = ", ".join(f"{b.agent_id} ({b.reason})" for b in blockers)
        super().__init__(
            "The agent registry has no approved version for the current definition of: "
            f"{names}. Run `borges agents publish` and `borges agents approve`, or set "
            "BORGES_REGISTRY_ENFORCE=false."
        )


def unapproved(fleet: Fleet, store: RegistryStore) -> list[Blocker]:
    blockers: list[Blocker] = []
    for descriptor in fleet.agents:
        if descriptor.lifecycle != "active":
            continue
        record = store.by_definition(descriptor.agent_id, descriptor.definition_sha)
        if record is None:
            reason = "unpublished change"
        elif record.state != "approved":
            reason = f"version {record.version} is {record.state}"
        else:
            continue
        blockers.append(
            Blocker(
                agent_id=descriptor.agent_id,
                definition_sha=descriptor.definition_sha,
                reason=reason,
            )
        )
    return blockers


def enforce_registry(settings: Settings, llm_mode: str) -> None:
    if not settings.borges_registry_enforce or llm_mode == "scripted":
        return
    blockers = unapproved(build_fleet(settings), open_store(settings))
    if blockers:
        raise RegistryBlocked(blockers)
