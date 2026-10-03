from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from pathlib import Path

from borges.config import Settings

UNKEYED_NOTICE = "unkeyed: tamper-evident only against accidental edits"
KEYED_NOTICE = "keyed: HMAC-SHA256 chain and signed anchor"
KEY_FILE_RELATIVE = Path("identity") / "store.key"
STORE_KEY_ENV = "BORGES_STORE_KEY"
EXISTING_STORES = (Path("identity") / "keys.jsonl", Path("fleet") / "registry.jsonl")


def store_key(settings: Settings) -> str | None:
    return settings.borges_store_key or settings.borges_audit_anchor_key or None


def derive_key(key: str, domain: str, purpose: str) -> str:
    material = f"{domain}\0{purpose}".encode()
    return hmac.new(key.encode("utf-8"), material, hashlib.sha256).hexdigest()


def notice_for(keyed: bool) -> str:
    return KEYED_NOTICE if keyed else UNKEYED_NOTICE


def write_key_file(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(secrets.token_hex(32))
    return path.read_text(encoding="utf-8").strip()


def read_key_file(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def ensure_store_key(settings: Settings) -> str | None:
    existing = store_key(settings)
    if existing:
        return existing
    home = Path(settings.borges_home)
    path = home / KEY_FILE_RELATIVE
    key = read_key_file(path)
    if key is None:
        if not settings.borges_store_key_autogen:
            return None
        if any((home / name).is_file() for name in EXISTING_STORES):
            return None
        key = write_key_file(path)
    os.environ[STORE_KEY_ENV] = key
    return key
