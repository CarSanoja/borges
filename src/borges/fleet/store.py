from __future__ import annotations

from pathlib import Path
from typing import Any

from borges.fleet.models import Approval
from borges.fleet.versions import Transition, VersionRecord, parse_version
from borges.identity.chain import ChainBroken, ChainedJsonl, ChainStatus

PUBLISHED = "version.published"
STATE_CHANGED = "state.changed"
ALLOWED = {
    "proposed": {"approved", "retired"},
    "approved": {"retired"},
    "retired": set(),
}


class TransitionError(ValueError):
    pass


class RegistryTampered(ChainBroken):
    def __init__(self, path: Path, line: int, reason: str) -> None:
        super().__init__(path, line, reason)
        self.args = (
            f"The agent registry at {path} failed hash-chain verification at line {line}: "
            f"{reason}. Refusing to use it; restore it from backup or delete it so it is "
            "re-imported from the tracked seed (`borges agents verify` re-checks it).",
        )


class RegistryStore:
    """Append-only JSONL of published agent versions and their approval transitions."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._chain = ChainedJsonl(self.path)

    def events(self) -> list[dict[str, Any]]:
        try:
            return self._chain.read()
        except ChainBroken as broken:
            raise RegistryTampered(broken.path, broken.line, broken.reason) from broken

    def verify(self) -> ChainStatus:
        return self._chain.verify()

    def _append(self, event: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._chain.append(event)
        except ChainBroken as broken:
            raise RegistryTampered(broken.path, broken.line, broken.reason) from broken

    def records(self) -> list[VersionRecord]:
        folded: dict[tuple[str, str], VersionRecord] = {}
        for event in self.events():
            key = (event["agent_id"], event["version"])
            if event["event"] == PUBLISHED:
                record = VersionRecord(
                    agent_id=event["agent_id"],
                    version=event["version"],
                    definition_sha=event["definition_sha"],
                    state=event["state"],
                    bump=event["bump"],
                    changelog=event["changelog"],
                    published_at=event["ts"],
                    published_by=event["by"],
                    descriptor=event["descriptor"],
                )
                record.history.append(
                    Transition(ts=event["ts"], state=event["state"], by=event["by"])
                )
                folded[key] = record
            elif event["event"] == STATE_CHANGED and key in folded:
                folded[key].state = event["to"]
                folded[key].history.append(
                    Transition(
                        ts=event["ts"],
                        state=event["to"],
                        by=event["by"],
                        reason=event.get("reason"),
                    )
                )
        return list(folded.values())

    def versions_of(self, agent_id: str) -> list[VersionRecord]:
        found = [r for r in self.records() if r.agent_id == agent_id]
        return sorted(found, key=lambda r: parse_version(r.version))

    def latest(self, agent_id: str) -> VersionRecord | None:
        versions = self.versions_of(agent_id)
        return versions[-1] if versions else None

    def get(self, agent_id: str, version: str) -> VersionRecord | None:
        return next((r for r in self.versions_of(agent_id) if r.version == version), None)

    def by_definition(self, agent_id: str, definition_sha: str) -> VersionRecord | None:
        matches = [r for r in self.versions_of(agent_id) if r.definition_sha == definition_sha]
        return matches[-1] if matches else None

    def publish(
        self,
        agent_id: str,
        version: str,
        definition_sha: str,
        descriptor: dict[str, Any],
        bump: str,
        changelog: str,
        by: str,
        state: Approval = "proposed",
    ) -> None:
        self._append(
            {
                "event": PUBLISHED,
                "agent_id": agent_id,
                "version": version,
                "definition_sha": definition_sha,
                "descriptor": descriptor,
                "bump": bump,
                "changelog": changelog,
                "state": state,
                "by": by,
            }
        )

    def transition(
        self, agent_id: str, version: str, to: Approval, by: str, reason: str | None = None
    ) -> VersionRecord:
        record = self.get(agent_id, version)
        if record is None:
            raise KeyError(f"{agent_id} {version}")
        if to not in ALLOWED[record.state]:
            raise TransitionError(f"{agent_id} {version} is {record.state}; cannot become {to}")
        self._append(
            {
                "event": STATE_CHANGED,
                "agent_id": agent_id,
                "version": version,
                "from": record.state,
                "to": to,
                "by": by,
                "reason": reason,
            }
        )
        return self.get(agent_id, version) or record
