from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.identity.chain import ChainBroken, ChainedJsonl


def test_append_chains_records_and_verifies(tmp_path: Path) -> None:
    chain = ChainedJsonl(tmp_path / "c.jsonl")
    first = chain.append({"event": "a"})
    second = chain.append({"event": "b"})
    assert second["prev_hash"] == first["hash"]
    assert [e["seq"] for e in chain.read()] == [1, 2]
    status = chain.verify()
    assert status.ok and status.records == 2 and status.head_hash == second["hash"]


def test_edited_record_is_detected_and_refused(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl"
    chain = ChainedJsonl(path)
    chain.append({"event": "a", "who": "alice"})
    chain.append({"event": "b"})
    path.write_text(path.read_text().replace("alice", "mallory"))
    fresh = ChainedJsonl(path)
    with pytest.raises(ChainBroken, match="line 1"):
        fresh.read()
    with pytest.raises(ChainBroken):
        fresh.append({"event": "c"})
    assert not fresh.verify().ok


def test_deleted_middle_record_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl"
    chain = ChainedJsonl(path)
    for name in "abc":
        chain.append({"event": name})
    lines = path.read_text().splitlines()
    path.write_text("\n".join([lines[0], lines[2]]) + "\n")
    status = ChainedJsonl(path).verify()
    assert not status.ok and status.broken_line == 2


def test_unreadable_line_breaks_the_chain(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl"
    path.write_text("not json\n")
    assert not ChainedJsonl(path).verify().ok


def test_legacy_unhashed_prefix_is_accepted_and_extended(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl"
    path.write_text(json.dumps({"seq": 1, "event": "old"}) + "\n")
    chain = ChainedJsonl(path)
    assert chain.verify().legacy == 1
    chain.append({"event": "new"})
    status = ChainedJsonl(path).verify()
    assert status.ok and status.records == 2


def test_seal_legacy_rewrites_with_hashes_and_keeps_the_head(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl"
    path.write_text(json.dumps({"seq": 1, "event": "old"}) + "\n")
    before = ChainedJsonl(path).verify().head_hash
    assert ChainedJsonl(path).seal_legacy() == 1
    after = ChainedJsonl(path).verify()
    assert after.legacy == 0 and after.head_hash == before


def test_missing_file_is_an_empty_valid_chain(tmp_path: Path) -> None:
    chain = ChainedJsonl(tmp_path / "none.jsonl")
    assert chain.read() == []
    assert chain.verify().ok
