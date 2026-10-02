from __future__ import annotations

from pydantic import BaseModel

from borges.config import Settings
from borges.fleet.descriptor import build_descriptor
from borges.fleet.models import AgentDescriptor
from borges.fleet.models_in_use import Provider
from borges.fleet.roster import ROSTER
from borges.telemetry.hashing import sha256_json


class Fleet(BaseModel):
    registry_sha: str
    agents: list[AgentDescriptor]

    def get(self, agent_id: str) -> AgentDescriptor | None:
        return next((a for a in self.agents if a.agent_id == agent_id), None)


def build_fleet(settings: Settings, provider: Provider = "nebius") -> Fleet:
    agents = [build_descriptor(item, settings, provider) for item in ROSTER]
    registry_sha = sha256_json(sorted((a.agent_id, a.definition_sha) for a in agents))
    return Fleet(registry_sha=registry_sha, agents=agents)
