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


def write_legacy(path: Path, rows: int = 1) -> None:
    lines = [json.dumps({"seq": n, "event": "old"}) for n in range(1, rows + 1)]
    path.write_text("\n".join(lines) + "\n")


def test_unhashed_records_are_refused_unless_legacy_is_allowed(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl"
    write_legacy(path)
    status = ChainedJsonl(path).verify()
    assert not status.ok and "no legacy" in (status.reason or "")


def test_legacy_prefix_is_attested_by_the_first_hashed_record(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl"
    write_legacy(path, 2)
    chain = ChainedJsonl(path, allow_legacy=True)
    assert not chain.verify().ok
    first = chain.append({"event": "new"})
    assert first["legacy_digest"] and first["seq"] == 3
    status = ChainedJsonl(path, allow_legacy=True).verify()
    assert status.ok and status.records == 3 and status.legacy == 2
    assert "legacy_digest" not in chain.append({"event": "next"})


def test_legacy_prefix_edited_after_attestation_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl"
    write_legacy(path, 2)
    ChainedJsonl(path, allow_legacy=True).append({"event": "new"})
    path.write_text(path.read_text().replace('"seq": 1', '"seq": 9', 1))
    status = ChainedJsonl(path, allow_legacy=True).verify()
    assert not status.ok and "not attested" in (status.reason or "")


def test_forged_legacy_prefix_without_attestation_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl"
    chain = ChainedJsonl(path, allow_legacy=True)
    chain.append({"event": "a"})
    chain.append({"event": "b"})
    forged = json.dumps({"seq": 1, "event": "forged"}) + "\n"
    path.write_text(forged + path.read_text())
    status = ChainedJsonl(path, allow_legacy=True).verify()
    assert not status.ok


def test_unattested_legacy_only_file_is_refused_until_migrated(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl"
    write_legacy(path)
    chain = ChainedJsonl(path, allow_legacy=True)
    assert chain.attest_legacy()
    assert ChainedJsonl(path, allow_legacy=True).verify().ok
    assert not chain.attest_legacy()


def test_keyed_chain_rejects_a_rewrite_that_recomputes_unkeyed_hashes(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl"
    chain = ChainedJsonl(path, key="secret", domain="d")
    chain.append({"event": "a"})
    forged = ChainedJsonl(tmp_path / "f.jsonl", domain="d")
    forged.append({"event": "a", "evil": True})
    path.write_text((tmp_path / "f.jsonl").read_text())
    status = ChainedJsonl(path, key="secret", domain="d").verify()
    assert not status.ok and "without a store key" in (status.reason or "")
    assert status.keyed


def test_keyed_hash_depends_on_key_and_domain(tmp_path: Path) -> None:
    one = ChainedJsonl(tmp_path / "1.jsonl", key="k1", domain="d")
    two = ChainedJsonl(tmp_path / "2.jsonl", key="k2", domain="d")
    other = ChainedJsonl(tmp_path / "3.jsonl", key="k1", domain="e")
    for chain in (one, two, other):
        chain.append({"event": "a"})
    assert len({c.verify().head_hash for c in (one, two, other)}) == 3
    assert not ChainedJsonl(tmp_path / "1.jsonl", key="k2", domain="d").verify().ok


def test_status_notice_names_the_mode(tmp_path: Path) -> None:
    plain = ChainedJsonl(tmp_path / "p.jsonl")
    keyed = ChainedJsonl(tmp_path / "k.jsonl", key="s")
    assert "tamper-evident only against accidental edits" in plain.verify().notice
    assert "tamper-evident only" not in keyed.verify().notice


def test_missing_file_is_an_empty_valid_chain(tmp_path: Path) -> None:
    chain = ChainedJsonl(tmp_path / "none.jsonl")
    assert chain.read() == []
    assert chain.verify().ok


def test_torn_last_line_is_ignored_on_read_and_quarantined_on_append(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl"
    chain = ChainedJsonl(path)
    first = chain.append({"event": "a"})
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"seq": 2, "event": "b", "prev_ha')
    fresh = ChainedJsonl(path)
    assert [e["event"] for e in fresh.read()] == ["a"]
    assert fresh.verify().ok
    nxt = fresh.append({"event": "c"})
    assert nxt["prev_hash"] == first["hash"] and nxt["seq"] == 2
    assert ChainedJsonl(path).verify().records == 2
    assert path.with_name("c.jsonl.torn").read_text().startswith('{"seq": 2')


def test_valid_last_record_missing_its_newline_is_kept(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl"
    chain = ChainedJsonl(path)
    chain.append({"event": "a"})
    path.write_text(path.read_text().rstrip("\n"))
    fresh = ChainedJsonl(path)
    assert len(fresh.read()) == 1
    fresh.append({"event": "b"})
    status = ChainedJsonl(path).verify()
    assert status.ok and status.records == 2
