from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from borges.config import Settings
from borges.identity.chain import ChainBroken
from borges.identity.keystore import KeyStore, KeyStoreError, open_keystore
from borges.telemetry.audit_log import AuditLog
from borges.telemetry.audit_verify import read_records


def build(tmp_path: Path, key: str | None = None) -> KeyStore:
    return KeyStore(tmp_path / "keys.jsonl", key, audit=AuditLog(tmp_path / "audit.jsonl"))


def snapshot(tmp_path: Path, label: str) -> None:
    for name in ("keys.jsonl", "keys.anchor.jsonl"):
        shutil.copy(tmp_path / name, tmp_path / f"{label}.{name}")


def restore(tmp_path: Path, label: str) -> None:
    for name in ("keys.jsonl", "keys.anchor.jsonl"):
        shutil.copy(tmp_path / f"{label}.{name}", tmp_path / name)


@pytest.mark.parametrize("key", [None, "secret"])
def test_rolling_back_chain_and_anchor_together_is_detected_after_a_key_was_created(
    tmp_path: Path, key: str | None
) -> None:
    store = build(tmp_path, key)
    store.create("alice", "audit:read")
    snapshot(tmp_path, "early")
    second, _ = store.create("bob", "audit:read")
    restore(tmp_path, "early")
    fresh = build(tmp_path, key)
    status = fresh.verify()
    assert not status.ok and second.key_id in (status.reason or "")
    assert "rolled back" in (status.reason or "")
    with pytest.raises(ChainBroken):
        fresh.records()
    with pytest.raises(ChainBroken):
        fresh.create("mallory", "audit:read")


@pytest.mark.parametrize("key", [None, "secret"])
def test_rolling_back_a_revocation_is_detected(tmp_path: Path, key: str | None) -> None:
    store = build(tmp_path, key)
    record, token = store.create("alice", "audit:read")
    snapshot(tmp_path, "before")
    store.revoke(record.key_id)
    restore(tmp_path, "before")
    fresh = build(tmp_path, key)
    found, failure = fresh.authenticate(token)
    assert found is None and failure == "store_broken"
    assert "revoked" in (fresh.verify().reason or "")


def test_truncating_both_files_to_nothing_is_detected(tmp_path: Path) -> None:
    store = build(tmp_path)
    store.create("alice", "audit:read")
    (tmp_path / "keys.jsonl").write_text("")
    (tmp_path / "keys.anchor.jsonl").write_text("")
    assert not build(tmp_path).verify().ok


def test_deleting_both_files_is_detected_while_the_audit_chain_remembers(tmp_path: Path) -> None:
    store = build(tmp_path)
    _, token = store.create("alice", "audit:read")
    (tmp_path / "keys.jsonl").unlink()
    (tmp_path / "keys.anchor.jsonl").unlink()
    assert build(tmp_path).authenticate(token) == (None, "store_broken")


def test_key_events_are_audited_with_the_key_id_and_record_number(tmp_path: Path) -> None:
    store = build(tmp_path)
    record, _ = store.create("alice", "audit:read")
    store.revoke(record.key_id)
    rows = read_records(tmp_path / "audit.jsonl")
    assert [r.kind for r in rows] == ["identity.key.created", "identity.key.revoked"]
    assert [r.data["key_id"] for r in rows] == [record.key_id] * 2
    assert [r.data["seq"] for r in rows] == [1, 2]
    assert "secret" not in str(rows[0].data) and "salt" not in str(rows[0].data)


def test_an_honest_store_keeps_working(tmp_path: Path) -> None:
    store = build(tmp_path)
    first, token = store.create("alice", "audit:read")
    store.create("bob", "audit:read")
    store.revoke(first.key_id)
    fresh = build(tmp_path)
    assert fresh.verify().ok and fresh.verify().records == 3
    assert fresh.authenticate(token) == (None, "revoked")


@pytest.mark.parametrize("anchored_audit", [False, True])
def test_a_running_server_refuses_a_store_whose_record_count_goes_backwards(
    tmp_path: Path, anchored_audit: bool
) -> None:
    audit = AuditLog(tmp_path / "audit.jsonl") if anchored_audit else None
    store = KeyStore(tmp_path / "keys.jsonl", audit=audit)
    store.create("alice", "audit:read")
    snapshot(tmp_path, "early")
    _, token = store.create("bob", "audit:read")
    assert store.authenticate(token)[1] is None
    restore(tmp_path, "early")
    if audit is not None:
        (tmp_path / "audit.jsonl").unlink()
    found, failure = store.authenticate(token)
    assert found is None and failure == "store_broken"
    assert "already saw 2" in (store.verify().reason or "")


def test_a_running_server_refuses_a_different_chain_of_the_same_length(tmp_path: Path) -> None:
    store = KeyStore(tmp_path / "keys.jsonl", anchored=False)
    store.create("alice", "audit:read")
    store.records()
    other = tmp_path / "other"
    other.mkdir()
    KeyStore(other / "keys.jsonl", anchored=False).create("mallory", "admin")
    shutil.copy(other / "keys.jsonl", tmp_path / "keys.jsonl")
    with pytest.raises(ChainBroken, match="replaced while running"):
        store.records()


def test_open_keystore_audits_into_the_global_chain(settings: Settings) -> None:
    store = open_keystore(settings)
    record, _ = store.create("alice", "audit:read")
    path = Path(settings.borges_home) / "audit" / "global.jsonl"
    assert [r.data["key_id"] for r in read_records(path)] == [record.key_id]


@pytest.mark.parametrize("name", ["anonymous", "legacy-live-token", "public-demo"])
def test_names_of_built_in_callers_and_tenants_cannot_be_issued(tmp_path: Path, name: str) -> None:
    with pytest.raises(KeyStoreError, match="reserved"):
        build(tmp_path).create(name, "memory:write")
