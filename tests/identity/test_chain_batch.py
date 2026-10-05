from __future__ import annotations

from pathlib import Path

from borges.identity.chain import ChainedJsonl

KEY = "k" * 32


def chain(path: Path) -> ChainedJsonl:
    return ChainedJsonl(path, key=KEY, anchor_path=path.with_name("anchor.jsonl"))


def bodies(store: ChainedJsonl) -> list[dict]:
    return [
        {k: v for k, v in e.items() if k not in {"ts", "hash", "prev_hash"}} for e in store.read()
    ]


def test_append_many_writes_the_same_chain_as_appending_one_at_a_time(tmp_path: Path) -> None:
    events = [{"event": "e", "n": i} for i in range(5)]
    single, batch = chain(tmp_path / "a" / "s.jsonl"), chain(tmp_path / "b" / "s.jsonl")
    single.append({"event": "start"})
    batch.append({"event": "start"})
    for event in events:
        single.append(event)
    written = batch.append_many(events)
    assert [r["seq"] for r in written] == [2, 3, 4, 5, 6]
    assert bodies(single) == bodies(batch)
    assert batch.verify().ok and batch.verify().records == 6
    assert chain(tmp_path / "b" / "s.jsonl").verify().ok


def test_append_many_with_nothing_writes_nothing(tmp_path: Path) -> None:
    store = chain(tmp_path / "s.jsonl")
    assert store.append_many([]) == []
    assert store.read() == []
