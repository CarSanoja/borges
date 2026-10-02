from __future__ import annotations

import json

from borges.config import Settings
from borges.fleet.fleet import Fleet
from borges.fleet.locations import home_store, import_seed, open_store, seed_store, store_path
from borges.fleet.store import RegistryStore


def test_seed_approves_the_current_definitions(fleet: Fleet) -> None:
    seed = seed_store()
    for descriptor in fleet.agents:
        record = seed.by_definition(descriptor.agent_id, descriptor.definition_sha)
        assert record is not None, f"{descriptor.agent_id} changed: run borges agents publish"
        assert record.state == "approved"


def test_open_store_starts_from_the_seed(settings: Settings) -> None:
    store = open_store(settings)
    assert store.path == store_path(settings)
    assert len(store.records()) == len(seed_store().records())


def test_import_seed_is_idempotent_and_keeps_local_versions(
    empty_store: RegistryStore,
) -> None:
    empty_store.publish("judge", "1.0.0", "local", {}, "major", "local", "me")
    seed = seed_store()
    first = import_seed(empty_store, seed)
    assert import_seed(empty_store, seed) == 0
    assert first == len(seed.records()) - 1
    assert empty_store.get("judge", "1.0.0").definition_sha == "local"


def test_open_store_attests_a_wave_one_legacy_registry(settings: Settings) -> None:
    path = store_path(settings)
    path.parent.mkdir(parents=True)
    legacy = {
        "seq": 1,
        "ts": 1.0,
        "event": "version.published",
        "agent_id": "judge",
        "version": "0.9.0",
        "definition_sha": "old",
        "descriptor": {},
        "bump": "major",
        "changelog": "old",
        "state": "approved",
        "by": "operator",
    }
    path.write_text(json.dumps(legacy) + "\n")
    store = open_store(settings)
    assert store.get("judge", "0.9.0") is not None
    assert open_store(settings).verify().ok


def test_open_store_anchors_the_registry_and_catches_truncation(settings: Settings) -> None:
    store = open_store(settings)
    lines = store.path.read_text().splitlines()
    store.path.write_text("\n".join(lines[:-1]) + "\n")
    assert not home_store(settings).verify().ok
