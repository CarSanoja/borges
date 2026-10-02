from __future__ import annotations

from borges.runtime.checkpoints import NullCheckpointStore, SqliteCheckpointStore


def test_save_replaces_the_row_of_the_same_key(db) -> None:
    store = SqliteCheckpointStore(db)
    store.save("r1", "stage:plan", 3, {"a": 1})
    store.save("r1", "stage:plan", 5, {"a": 2})
    assert store.load("r1", "stage:plan") == {"a": 2}
    assert store.load("r1", "missing") is None
    assert store.load("r2", "stage:plan") is None


def test_prefix_listing_is_ordered_by_sequence(db) -> None:
    store = SqliteCheckpointStore(db)
    store.save("r1", "universe:b", 9, {"n": 2})
    store.save("r1", "universe:a", 4, {"n": 1})
    store.save("r1", "stage:plan", 1, {"n": 0})
    rows = store.with_prefix("r1", "universe:")
    assert [(key, seq) for key, seq, _ in rows] == [("universe:a", 4), ("universe:b", 9)]


def test_last_describes_the_most_recent_checkpoint(db) -> None:
    store = SqliteCheckpointStore(db)
    assert store.last("r1") is None
    store.save("r1", "stage:plan", 1, {})
    store.save("r1", "universe:a", 4, {})
    last = store.last("r1")
    assert last["key"] == "universe:a" and last["seq"] == 4 and last["checkpoints"] == 2


def test_clear_removes_only_that_run(db) -> None:
    store = SqliteCheckpointStore(db)
    store.save("r1", "k", 1, {})
    store.save("r2", "k", 1, {})
    store.clear("r1")
    assert store.load("r1", "k") is None and store.load("r2", "k") == {}


def test_null_store_remembers_nothing() -> None:
    store = NullCheckpointStore()
    store.save("r", "k", 1, {"a": 1})
    assert store.load("r", "k") is None
    assert store.with_prefix("r", "k") == [] and store.last("r") is None
    store.clear("r")
