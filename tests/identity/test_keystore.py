from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.identity.keystore import KeyStore, KeyStoreError


@pytest.fixture
def store(tmp_path: Path) -> KeyStore:
    return KeyStore(tmp_path / "keys.jsonl")


def test_create_returns_a_secret_that_authenticates(store: KeyStore) -> None:
    record, token = store.create("alice", "uploads:write,audit:read")
    found, failure = store.authenticate(token)
    assert failure is None and found is not None
    principal = found.principal()
    assert principal.id == "caller://alice"
    assert principal.has("uploads:write") and principal.has("cases:read")
    assert not principal.has("registry:approve")
    assert record.key_id in token


def test_only_a_salted_hash_is_stored(store: KeyStore, tmp_path: Path) -> None:
    _, token = store.create("alice", "audit:read")
    secret = token.split("_", 2)[2]
    raw = (tmp_path / "keys.jsonl").read_text()
    assert secret not in raw and token not in raw
    event = json.loads(raw.splitlines()[0])
    assert event["salt"] and len(event["secret_hash"]) == 64


def test_wrong_secret_unknown_key_and_malformed_fail(store: KeyStore) -> None:
    record, _ = store.create("alice", "audit:read")
    assert store.authenticate(f"bk_{record.key_id}_wrong")[1] == "bad_secret"
    assert store.authenticate("bk_ffffffffffff_x")[1] == "unknown_key"
    assert store.authenticate("garbage")[1] == "malformed"


def test_revoked_key_fails(store: KeyStore) -> None:
    record, token = store.create("alice", "audit:read")
    store.revoke(record.key_id)
    assert store.authenticate(token)[1] == "revoked"
    with pytest.raises(KeyStoreError, match="already revoked"):
        store.revoke(record.key_id)


def test_expired_key_fails(store: KeyStore) -> None:
    _, token = store.create("alice", "audit:read", ttl_s=60, now=1000.0)
    assert store.authenticate(token, now=1030.0)[1] is None
    assert store.authenticate(token, now=1061.0)[1] == "expired"


def test_unknown_scope_and_bad_name_are_rejected(store: KeyStore) -> None:
    with pytest.raises(ValueError, match="unknown scope"):
        store.create("alice", "root")
    with pytest.raises(KeyStoreError):
        store.create("Alice B", "audit:read")


def test_tampered_store_fails_closed(store: KeyStore, tmp_path: Path) -> None:
    _, token = store.create("alice", "audit:read")
    path = tmp_path / "keys.jsonl"
    path.write_text(path.read_text().replace("audit:read", "admin"))
    fresh = KeyStore(path)
    assert fresh.authenticate(token)[1] == "store_broken"
    assert not fresh.verify().ok


def test_revocation_by_another_process_is_seen(store: KeyStore, tmp_path: Path) -> None:
    record, token = store.create("alice", "audit:read")
    assert store.authenticate(token)[0] is not None
    KeyStore(tmp_path / "keys.jsonl").revoke(record.key_id)
    assert store.authenticate(token)[1] == "revoked"


def test_listing_orders_by_creation(store: KeyStore) -> None:
    store.create("a", "audit:read")
    store.create("b", "audit:read")
    assert [r.name for r in store.listing()] == ["a", "b"]
