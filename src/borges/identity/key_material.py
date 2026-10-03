from __future__ import annotations

import os
from pathlib import Path

from borges.config import Settings
from borges.identity.store_key import (
    ensure_store_key,
    read_key_file,
    write_key_file,
)
from borges.telemetry.audit_anchor import anchor_path_for
from borges.telemetry.run_telemetry import global_audit_path

ANCHOR_KEY_FILE = Path("identity") / "anchor.key"
MEMORY_KEY_FILE = Path("identity") / "memory.key"
ANCHOR_KEY_ENV = "BORGES_AUDIT_ANCHOR_KEY"
MEMORY_KEY_ENV = "BORGES_MEMORY_KEY"


def _load_or_create(path: Path, env_name: str, create: bool) -> str | None:
    key = read_key_file(path)
    if key is None:
        if not create:
            return None
        key = write_key_file(path)
    os.environ[env_name] = key
    return key


def ensure_anchor_key(settings: Settings, store_keyed: bool) -> str | None:
    if settings.borges_audit_anchor_key:
        return settings.borges_audit_anchor_key
    path = Path(settings.borges_home) / ANCHOR_KEY_FILE
    anchors = anchor_path_for(global_audit_path(settings))
    create = settings.borges_store_key_autogen and store_keyed and not anchors.is_file()
    return _load_or_create(path, ANCHOR_KEY_ENV, create)


def ensure_memory_key(settings: Settings) -> str | None:
    if settings.borges_memory_key:
        return settings.borges_memory_key
    if not settings.borges_memory:
        return None
    path = Path(settings.borges_home) / MEMORY_KEY_FILE
    return _load_or_create(path, MEMORY_KEY_ENV, settings.borges_store_key_autogen)


def ensure_keys(settings: Settings) -> dict[str, bool]:
    store = ensure_store_key(settings)
    anchor = ensure_anchor_key(settings, store is not None)
    memory = ensure_memory_key(settings)
    return {"store": store is not None, "anchor": anchor is not None, "memory": memory is not None}
