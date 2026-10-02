from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.identity.chain import ChainBroken, ChainedJsonl


def build(tmp_path: Path, key: str | None = None) -> ChainedJsonl:
    return ChainedJsonl(
        tmp_path / "c.jsonl", key=key, domain="d", anchor_path=tmp_path / "c.anchor.jsonl"
    )


@pytest.mark.parametrize("key", [None, "secret"])
def test_every_append_writes_an_anchor(tmp_path: Path, key: str | None) -> None:
    chain = build(tmp_path, key)
    chain.append({"event": "a"})
    last = chain.append({"event": "b"})
    anchors = (tmp_path / "c.anchor.jsonl").read_text().splitlines()
    assert len(anchors) == 2
    assert json.loads(anchors[-1])["head_hash"] == last["hash"]


@pytest.mark.parametrize("key", [None, "secret"])
def test_truncating_the_tail_fails_closed(tmp_path: Path, key: str | None) -> None:
    chain = build(tmp_path, key)
    for name in "abc":
        chain.append({"event": name})
    lines = (tmp_path / "c.jsonl").read_text().splitlines()
    (tmp_path / "c.jsonl").write_text("\n".join(lines[:-1]) + "\n")
    fresh = build(tmp_path, key)
    status = fresh.verify()
    assert not status.ok and "truncated" in (status.reason or "")
    with pytest.raises(ChainBroken):
        fresh.read()
    with pytest.raises(ChainBroken):
        fresh.append({"event": "d"})


def test_emptying_the_file_fails_closed(tmp_path: Path) -> None:
    chain = build(tmp_path)
    chain.append({"event": "a"})
    (tmp_path / "c.jsonl").write_text("")
    assert not build(tmp_path).verify().ok


def test_a_record_cut_mid_line_does_not_hide_the_truncation(tmp_path: Path) -> None:
    chain = build(tmp_path)
    chain.append({"event": "a"})
    chain.append({"event": "b"})
    text = (tmp_path / "c.jsonl").read_text()
    (tmp_path / "c.jsonl").write_text(text[: text.rfind("\n", 0, len(text) - 1) + 20])
    assert not build(tmp_path).verify().ok


def test_a_replaced_chain_diverges_from_the_anchor(tmp_path: Path) -> None:
    chain = build(tmp_path)
    chain.append({"event": "a"})
    chain.append({"event": "b"})
    other = ChainedJsonl(tmp_path / "o.jsonl", domain="d")
    other.append({"event": "x"})
    other.append({"event": "y"})
    (tmp_path / "c.jsonl").write_text((tmp_path / "o.jsonl").read_text())
    status = build(tmp_path).verify()
    assert not status.ok and "diverges" in (status.reason or "")


def test_a_crash_between_record_and_anchor_is_tolerated(tmp_path: Path) -> None:
    chain = build(tmp_path)
    chain.append({"event": "a"})
    anchors = (tmp_path / "c.anchor.jsonl").read_text()
    chain.append({"event": "b"})
    (tmp_path / "c.anchor.jsonl").write_text(anchors)
    assert build(tmp_path).verify().ok
    build(tmp_path).append({"event": "c"})
    assert build(tmp_path).verify().records == 3


def test_keyed_chain_needs_its_anchor_file(tmp_path: Path) -> None:
    chain = build(tmp_path, "secret")
    chain.append({"event": "a"})
    (tmp_path / "c.anchor.jsonl").unlink()
    assert not build(tmp_path, "secret").verify().ok


def test_unkeyed_chain_adopts_a_missing_anchor_on_the_next_append(tmp_path: Path) -> None:
    chain = build(tmp_path)
    chain.append({"event": "a"})
    (tmp_path / "c.anchor.jsonl").unlink()
    assert build(tmp_path).verify().ok
    build(tmp_path).append({"event": "b"})
    assert (tmp_path / "c.anchor.jsonl").is_file()


def test_edited_anchor_is_rejected_when_keyed(tmp_path: Path) -> None:
    chain = build(tmp_path, "secret")
    chain.append({"event": "a"})
    chain.append({"event": "b"})
    path = tmp_path / "c.anchor.jsonl"
    anchors = [json.loads(line) for line in path.read_text().splitlines()]
    anchors[-1]["count"] = 1
    path.write_text("\n".join(json.dumps(a) for a in anchors) + "\n")
    assert not build(tmp_path, "secret").verify().ok


def test_unkeyed_anchor_can_be_recomputed_by_a_file_writer(tmp_path: Path) -> None:
    chain = build(tmp_path)
    chain.append({"event": "a"})
    chain.append({"event": "b"})
    lines = (tmp_path / "c.jsonl").read_text().splitlines()
    (tmp_path / "c.jsonl").write_text(lines[0] + "\n")
    (tmp_path / "c.anchor.jsonl").unlink()
    assert build(tmp_path).verify().ok
