from __future__ import annotations

from pathlib import Path

from borges.config import Settings
from borges.fleet.store import RegistryStore

SEED_PATH = Path(__file__).resolve().parent / "registry_seed.jsonl"
STORE_RELATIVE = Path("fleet") / "registry.jsonl"
SEED_ACTOR = "seed"


def seed_store() -> RegistryStore:
    return RegistryStore(SEED_PATH)


def store_path(settings: Settings) -> Path:
    return Path(settings.borges_home) / STORE_RELATIVE


def import_seed(store: RegistryStore, seed: RegistryStore) -> int:
    imported = 0
    known = {(r.agent_id, r.definition_sha) for r in store.records()}
    taken = {(r.agent_id, r.version) for r in store.records()}
    for record in seed.records():
        key = (record.agent_id, record.definition_sha)
        if key in known or (record.agent_id, record.version) in taken:
            continue
        store.publish(
            record.agent_id,
            record.version,
            record.definition_sha,
            record.descriptor,
            record.bump,
            record.changelog,
            record.published_by,
            state=record.history[0].state,
        )
        for step in record.history[1:]:
            store.transition(record.agent_id, record.version, step.state, step.by, step.reason)
        imported += 1
    return imported


def open_store(settings: Settings) -> RegistryStore:
    store = RegistryStore(store_path(settings))
    import_seed(store, seed_store())
    return store
