from __future__ import annotations

from pathlib import Path

from borges.config import Settings
from borges.fleet.store import RegistryStore
from borges.identity.store_key import store_key

SEED_PATH = Path(__file__).resolve().parent / "registry_seed.jsonl"
STORE_RELATIVE = Path("fleet") / "registry.jsonl"
SEED_ACTOR = "seed"


def seed_store() -> RegistryStore:
    return RegistryStore(SEED_PATH)


def store_path(settings: Settings) -> Path:
    return Path(settings.borges_home) / STORE_RELATIVE


def import_seed(store: RegistryStore, seed: RegistryStore) -> int:
    known = {(r.agent_id, r.definition_sha) for r in store.records()}
    taken = {(r.agent_id, r.version) for r in store.records()}
    fresh = [
        record
        for record in seed.records()
        if (record.agent_id, record.definition_sha) not in known
        and (record.agent_id, record.version) not in taken
    ]
    store.import_records(fresh)
    return len(fresh)


def home_store(settings: Settings) -> RegistryStore:
    return RegistryStore(store_path(settings), key=store_key(settings), anchored=True, legacy=True)


def open_store(settings: Settings) -> RegistryStore:
    store = home_store(settings)
    store.attest_legacy()
    import_seed(store, seed_store())
    return store
