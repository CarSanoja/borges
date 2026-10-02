from __future__ import annotations

from borges.config import Settings
from borges.fleet.fleet import build_fleet
from borges.fleet.principal import agent_id_of


def capabilities_of(settings: Settings, principal: str) -> frozenset[str]:
    agent_id = agent_id_of(principal)
    descriptor = build_fleet(settings).get(agent_id) if agent_id else None
    return frozenset(descriptor.capabilities) if descriptor else frozenset()


def allows(settings: Settings, principal: str, capability: str) -> bool:
    return capability in capabilities_of(settings, principal)
