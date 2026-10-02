from __future__ import annotations

import fcntl
import json
import time
from pathlib import Path
from typing import Any

from borges.fleet.models import Approval
from borges.fleet.versions import Transition, VersionRecord, parse_version

PUBLISHED = "version.published"
STATE_CHANGED = "state.changed"
ALLOWED = {
    "proposed": {"approved", "retired"},
    "approved": {"retired"},
    "retired": set(),
}


class TransitionError(ValueError):
    pass


class RegistryStore:
    """Append-only JSONL of published agent versions and their approval transitions."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def events(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def _append(self, event: dict[str, Any]) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            handle.seek(0)
            seq = sum(1 for line in handle if line.strip()) + 1
            record = {"seq": seq, "ts": time.time(), **event}
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()
        return record

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
