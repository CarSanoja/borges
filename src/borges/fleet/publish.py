from __future__ import annotations

from pydantic import BaseModel

from borges.fleet.fleet import Fleet
from borges.fleet.semver import bump_kind, changed_fields, changelog_line, next_version
from borges.fleet.store import RegistryStore


class Published(BaseModel):
    agent_id: str
    version: str
    bump: str
    changelog: str
    definition_sha: str


def publish_fleet(
    store: RegistryStore, fleet: Fleet, by: str, message: str | None = None
) -> list[Published]:
    published: list[Published] = []
    for descriptor in fleet.agents:
        latest = store.latest(descriptor.agent_id)
        if latest is not None and latest.definition_sha == descriptor.definition_sha:
            continue
        current = descriptor.model_dump(mode="json", exclude={"field_sources"})
        previous = latest.descriptor if latest else {}
        changed = changed_fields(previous, current) if latest else []
        kind = bump_kind(changed) if latest else "major"
        version = next_version(latest.version if latest else None, kind)
        changelog = changelog_line(changed, previous, current)
        if message:
            changelog = f"{changelog}; {message}"
        store.publish(
            descriptor.agent_id,
            version,
            descriptor.definition_sha,
            current,
            kind,
            changelog,
            by,
        )
        published.append(
            Published(
                agent_id=descriptor.agent_id,
                version=version,
                bump=kind,
                changelog=changelog,
                definition_sha=descriptor.definition_sha,
            )
        )
    return published
