"""The versions the shipped seed records, so a republished agent does not break version checks."""

from __future__ import annotations

import json

from borges.fleet import locations


def seed_versions(agent_id: str) -> list[str]:
    lines = locations.SEED_PATH.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    return list(dict.fromkeys(r["version"] for r in rows if r["agent_id"] == agent_id))


def seed_version(agent_id: str) -> str:
    return seed_versions(agent_id)[-1]
