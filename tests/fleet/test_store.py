from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.fleet.locations import seed_store
from borges.fleet.store import RegistryStore, RegistryTampered, TransitionError


def put(store: RegistryStore, version: str, sha: str) -> None:
    store.publish("judge", version, sha, {"agent_id": "judge"}, "minor", "log", "tester")


def test_publish_and_fold(empty_store: RegistryStore) -> None:
    put(empty_store, "1.0.0", "a")
    put(empty_store, "1.1.0", "b")
    latest = empty_store.latest("judge")
    assert latest is not None and latest.version == "1.1.0" and latest.state == "proposed"
    assert [r.version for r in empty_store.versions_of("judge")] == ["1.0.0", "1.1.0"]
    assert empty_store.by_definition("judge", "a").version == "1.0.0"
    assert empty_store.latest("other") is None


def test_versions_sort_numerically(empty_store: RegistryStore) -> None:
    put(empty_store, "1.9.0", "a")
    put(empty_store, "1.10.0", "b")
    assert empty_store.latest("judge").version == "1.10.0"


def test_transitions_follow_the_lifecycle(empty_store: RegistryStore) -> None:
    put(empty_store, "1.0.0", "a")
    approved = empty_store.transition("judge", "1.0.0", "approved", "boss", "ok")
    assert approved.state == "approved" and approved.history[-1].by == "boss"
    assert empty_store.transition("judge", "1.0.0", "retired", "boss").state == "retired"
    with pytest.raises(TransitionError):
        empty_store.transition("judge", "1.0.0", "approved", "boss")


def test_approved_cannot_go_back_to_proposed(empty_store: RegistryStore) -> None:
    put(empty_store, "1.0.0", "a")
    empty_store.transition("judge", "1.0.0", "approved", "boss")
    with pytest.raises(TransitionError):
        empty_store.transition("judge", "1.0.0", "proposed", "boss")


def test_unknown_version_is_a_key_error(empty_store: RegistryStore) -> None:
    with pytest.raises(KeyError):
        empty_store.transition("judge", "9.9.9", "approved", "boss")


def test_store_is_append_only(empty_store: RegistryStore) -> None:
    put(empty_store, "1.0.0", "a")
    first = empty_store.path.read_text()
    empty_store.transition("judge", "1.0.0", "approved", "boss")
    assert empty_store.path.read_text().startswith(first)
    assert [e["seq"] for e in empty_store.events()] == [1, 2]


def filled(path: Path) -> RegistryStore:
    store = RegistryStore(path)
    store.publish("judge", "1.0.0", "sha-a", {}, "major", "first", "alice")
    store.transition("judge", "1.0.0", "approved", "bob", "ok")
    return store


def test_records_are_hash_chained(tmp_path: Path) -> None:
    path = tmp_path / "registry.jsonl"
    filled(path)
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    assert lines[0]["prev_hash"] == "0" * 64
    assert lines[1]["prev_hash"] == lines[0]["hash"]
    assert RegistryStore(path).verify().ok


def test_editing_an_approval_breaks_the_store(tmp_path: Path) -> None:
    path = tmp_path / "registry.jsonl"
    filled(path)
    path.write_text(path.read_text().replace('"by":"bob"', '"by":"alice"'))
    store = RegistryStore(path)
    with pytest.raises(RegistryTampered, match="Refusing to use it"):
        store.records()
    assert not store.verify().ok


def test_forging_an_approved_state_in_place_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "registry.jsonl"
    store = RegistryStore(path)
    store.publish("judge", "1.0.0", "sha-a", {}, "major", "first", "alice")
    path.write_text(path.read_text().replace('"state":"proposed"', '"state":"approved"'))
    with pytest.raises(RegistryTampered):
        RegistryStore(path).get("judge", "1.0.0")


def test_deleting_a_record_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "registry.jsonl"
    store = filled(path)
    store.publish("coder", "1.0.0", "sha-c", {}, "major", "first", "alice")
    lines = path.read_text().splitlines()
    path.write_text("\n".join([lines[0], lines[2]]) + "\n")
    with pytest.raises(RegistryTampered):
        RegistryStore(path).records()


def test_a_broken_store_refuses_new_writes(tmp_path: Path) -> None:
    path = tmp_path / "registry.jsonl"
    filled(path)
    path.write_text(path.read_text().replace("sha-a", "sha-z"))
    with pytest.raises(RegistryTampered):
        RegistryStore(path).publish("coder", "1.0.0", "sha-c", {}, "major", "x", "alice")


def test_an_unhashed_legacy_store_is_accepted_and_extended(tmp_path: Path) -> None:
    path = tmp_path / "registry.jsonl"
    legacy = {
        "seq": 1,
        "ts": 1.0,
        "event": "version.published",
        "agent_id": "judge",
        "version": "1.0.0",
        "definition_sha": "sha-a",
        "descriptor": {},
        "bump": "major",
        "changelog": "old",
        "state": "approved",
        "by": "operator",
    }
    path.write_text(json.dumps(legacy) + "\n")
    store = RegistryStore(path)
    assert store.get("judge", "1.0.0").state == "approved"
    store.publish("coder", "1.0.0", "sha-c", {}, "major", "new", "alice")
    assert RegistryStore(path).verify().ok


def test_the_tracked_seed_is_sealed_and_intact() -> None:
    status = seed_store().verify()
    assert status.ok and status.legacy == 0 and status.records > 0
