from __future__ import annotations

from borges.config import Settings
from borges.fleet.fleet import Fleet, build_fleet


def test_fleet_lists_agents_and_components(fleet: Fleet) -> None:
    assert len(fleet.agents) == 12
    assert fleet.get("judge") is not None and fleet.get("nobody") is None


def test_registry_sha_tracks_definitions(settings: Settings, fleet: Fleet) -> None:
    assert build_fleet(settings).registry_sha == fleet.registry_sha
    assert build_fleet(settings, "local").registry_sha != fleet.registry_sha
