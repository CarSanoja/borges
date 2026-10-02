from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.config import Settings
from borges.identity import api_key
from borges.identity.chain import ChainBroken
from borges.identity.keystore import KeyStore, KeyStoreError, open_keystore


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


def truncate_last_line(path: Path) -> None:
    lines = path.read_text().splitlines()
    path.write_text("\n".join(lines[:-1]) + "\n")


@pytest.mark.parametrize("key", [None, "store-secret"])
def test_deleting_the_last_line_cannot_resurrect_a_revoked_key(
    tmp_path: Path, key: str | None
) -> None:
    path = tmp_path / "keys.jsonl"
    store = KeyStore(path, key)
    first, token = store.create("alice", "audit:read")
    store.create("bob", "audit:read")
    store.revoke(first.key_id)
    assert store.authenticate(token)[1] == "revoked"
    truncate_last_line(path)
    fresh = KeyStore(path, key)
    assert not fresh.verify().ok
    assert fresh.authenticate(token) == (None, "store_broken")


def forged_admin_line(key_id: str, secret: str) -> str:
    salt = "ab" * 8
    event = {
        "seq": 1,
        "ts": 1.0,
        "event": "key.created",
        "key_id": key_id,
        "name": "evil",
        "scopes": ["admin"],
        "salt": salt,
        "secret_hash": api_key.hash_secret(salt, secret),
        "expires_at": None,
    }
    return json.dumps(event) + "\n"


@pytest.mark.parametrize("key", [None, "store-secret"])
def test_a_handwritten_unhashed_record_is_refused(tmp_path: Path, key: str | None) -> None:
    path = tmp_path / "keys.jsonl"
    path.write_text(forged_admin_line("ffffffffffff", "forged"))
    store = KeyStore(path, key)
    status = store.verify()
    assert not status.ok and "unhashed" in (status.reason or "")
    token = api_key.format_token("ffffffffffff", "forged")
    assert store.authenticate(token) == (None, "store_broken")
    with pytest.raises(ChainBroken):
        store.create("carol", "audit:read")


def test_a_forged_unhashed_record_in_front_of_real_ones_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "keys.jsonl"
    store = KeyStore(path)
    store.create("alice", "audit:read")
    path.write_text(forged_admin_line("ffffffffffff", "forged") + path.read_text())
    assert not KeyStore(path).verify().ok


def test_a_keyed_store_rejects_a_chain_recomputed_without_the_key(tmp_path: Path) -> None:
    path = tmp_path / "keys.jsonl"
    KeyStore(path, "store-secret").create("alice", "audit:read")
    forged = tmp_path / "other" / "keys.jsonl"
    attacker = KeyStore(forged)
    _, token = attacker.create("evil", "admin")
    path.write_text(forged.read_text())
    victim = KeyStore(path, "store-secret")
    assert victim.authenticate(token) == (None, "store_broken")


def test_open_keystore_uses_the_store_key_and_falls_back_to_the_anchor_key(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    stored = Settings(_env_file=None, borges_home=home, borges_store_key="a")
    open_keystore(stored).create("alice", "audit:read")
    assert open_keystore(stored).verify().keyed
    fallback = Settings(_env_file=None, borges_home=tmp_path / "h2", borges_audit_anchor_key="b")
    assert open_keystore(fallback).verify().keyed
    assert not open_keystore(Settings(_env_file=None, borges_home=tmp_path / "h3")).verify().keyed
    wrong = Settings(_env_file=None, borges_home=home, borges_store_key="z")
    assert not open_keystore(wrong).verify().ok
