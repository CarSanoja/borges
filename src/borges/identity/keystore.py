from __future__ import annotations

import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

from borges.config import Settings
from borges.identity import api_key
from borges.identity.chain import ChainBroken, ChainedJsonl, ChainStatus
from borges.identity.principal import Principal, caller_principal
from borges.identity.scopes import PUBLIC_SCOPES, parse_scopes
from borges.identity.store_key import store_key

KEYS_RELATIVE = Path("identity") / "keys.jsonl"
KEYS_DOMAIN = "identity.keys"
CREATED = "key.created"
REVOKED = "key.revoked"

AuthFailure = Literal[
    "malformed", "unknown_key", "bad_secret", "revoked", "expired", "store_broken"
]


class KeyStoreError(ValueError):
    pass


@dataclass(frozen=True)
class KeyRecord:
    key_id: str
    name: str
    scopes: frozenset[str]
    created_at: float
    expires_at: float | None
    salt: str
    secret_hash: str
    revoked_at: float | None = None

    @property
    def principal_id(self) -> str:
        return caller_principal(self.name)

    def status(self, now: float) -> Literal["active", "revoked", "expired"]:
        if self.revoked_at is not None:
            return "revoked"
        if self.expires_at is not None and now >= self.expires_at:
            return "expired"
        return "active"

    def principal(self) -> Principal:
        return Principal(
            id=self.principal_id,
            kind="key",
            scopes=self.scopes | PUBLIC_SCOPES,
            key_id=self.key_id,
            expires_at=self.expires_at,
        )


def anchor_path_for(path: Path) -> Path:
    return path.with_name(path.stem + ".anchor.jsonl")


def keys_path(settings: Settings) -> Path:
    return Path(settings.borges_home) / KEYS_RELATIVE


def _fold(events: list[dict[str, Any]]) -> dict[str, KeyRecord]:
    keys: dict[str, KeyRecord] = {}
    for event in events:
        if event["event"] == CREATED:
            keys[event["key_id"]] = KeyRecord(
                key_id=event["key_id"],
                name=event["name"],
                scopes=frozenset(event["scopes"]),
                created_at=event["ts"],
                expires_at=event.get("expires_at"),
                salt=event["salt"],
                secret_hash=event["secret_hash"],
            )
        elif event["event"] == REVOKED and event["key_id"] in keys:
            keys[event["key_id"]] = replace(keys[event["key_id"]], revoked_at=event["ts"])
    return keys


class KeyStore:
    """Append-only, hash-chained store of API keys; only salted secret hashes are kept."""

    def __init__(self, path: Path, key: str | None = None, anchored: bool = True) -> None:
        self.path = Path(path)
        self.anchor_path = anchor_path_for(self.path)
        self._chain = ChainedJsonl(
            self.path,
            key=key,
            domain=KEYS_DOMAIN,
            anchor_path=self.anchor_path if anchored else None,
        )

    def verify(self) -> ChainStatus:
        return self._chain.verify()

    def records(self) -> dict[str, KeyRecord]:
        return _fold(self._chain.read())

    def listing(self) -> list[KeyRecord]:
        return sorted(self.records().values(), key=lambda r: r.created_at)

    def create(
        self,
        name: str,
        scopes: str | frozenset[str],
        ttl_s: float | None = None,
        now: float | None = None,
    ) -> tuple[KeyRecord, str]:
        if not api_key.valid_name(name):
            raise KeyStoreError(
                "key names use lowercase letters, digits, dots, dashes and underscores"
            )
        granted = parse_scopes(scopes) if isinstance(scopes, str) else scopes
        key_id, secret, salt = api_key.new_key_id(), api_key.new_secret(), api_key.new_salt()
        issued = now if now is not None else time.time()
        record = self._chain.append(
            {
                "event": CREATED,
                "key_id": key_id,
                "name": name,
                "scopes": sorted(granted),
                "salt": salt,
                "secret_hash": api_key.hash_secret(salt, secret),
                "expires_at": issued + ttl_s if ttl_s else None,
            }
        )
        created = _fold([record])[key_id]
        return created, api_key.format_token(key_id, secret)

    def revoke(self, key_id: str) -> KeyRecord:
        current = self.records().get(key_id)
        if current is None:
            raise KeyStoreError(f"unknown key '{key_id}'")
        if current.revoked_at is not None:
            raise KeyStoreError(f"key '{key_id}' is already revoked")
        self._chain.append({"event": REVOKED, "key_id": key_id})
        return self.records()[key_id]

    def authenticate(
        self, token: str, now: float | None = None
    ) -> tuple[KeyRecord | None, AuthFailure | None]:
        parsed = api_key.parse_token(token)
        if parsed is None:
            return None, "malformed"
        key_id, secret = parsed
        try:
            records = self.records()
        except ChainBroken:
            return None, "store_broken"
        record = records.get(key_id)
        if record is None:
            return None, "unknown_key"
        if not api_key.secret_matches(record.salt, record.secret_hash, secret):
            return None, "bad_secret"
        state = record.status(now if now is not None else time.time())
        if state != "active":
            return None, state
        return record, None


def open_keystore(settings: Settings) -> KeyStore:
    return KeyStore(keys_path(settings), store_key(settings))
