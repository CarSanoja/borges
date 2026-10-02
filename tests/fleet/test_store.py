from __future__ import annotations

import pytest

from borges.fleet.store import RegistryStore, TransitionError


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
