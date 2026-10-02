from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.telemetry.audit_anchor import (
    AnchorConfig,
    anchor_path_for,
    latest_anchor,
    read_anchors,
    write_anchor,
)
from borges.telemetry.audit_log import AuditLog, checkpoint


def make(tmp_path: Path, every: int = 3, key: str | None = None) -> tuple[AuditLog, AnchorConfig]:
    path = tmp_path / "global.jsonl"
    config = AnchorConfig(anchor_path_for(path), key, every)
    return AuditLog(path, config), config


def test_anchor_path_sits_next_to_the_log(tmp_path: Path) -> None:
    assert anchor_path_for(tmp_path / "global.jsonl") == tmp_path / "global.anchor.jsonl"


def test_checkpoint_is_written_every_n_records(tmp_path: Path) -> None:
    log, config = make(tmp_path, every=3)
    for index in range(7):
        log.append(f"k{index}")
    anchors = read_anchors(config.path)
    assert [a.count for a in anchors] == [3, 6]
    assert anchors[-1].head_hash
    assert anchors[1].prev == anchors[0].mac


def test_checkpoint_at_shutdown_covers_the_tail_once(tmp_path: Path) -> None:
    log, config = make(tmp_path, every=100)
    log.append("a")
    log.append("b")
    assert checkpoint(log.path, config) is True
    assert checkpoint(log.path, config) is False
    assert latest_anchor(config.path).count == 2


def test_empty_log_has_nothing_to_anchor(tmp_path: Path) -> None:
    log, config = make(tmp_path)
    assert checkpoint(log.path, config) is False


def test_signed_anchor_uses_hmac_when_a_key_is_set(tmp_path: Path) -> None:
    signed = write_anchor(AnchorConfig(tmp_path / "a.jsonl", "secret", 1), 1, "h" * 64)
    plain = write_anchor(AnchorConfig(tmp_path / "b.jsonl", None, 1), 1, "h" * 64)
    assert signed.alg == "hmac-sha256" and plain.alg == "sha256"
    assert signed.mac != plain.mac


def test_anchor_lines_are_valid_json_with_the_documented_fields(tmp_path: Path) -> None:
    log, config = make(tmp_path, every=1, key="k")
    log.append("a")
    line = json.loads(config.path.read_text().splitlines()[0])
    assert {"count", "head_hash", "ts", "mac", "alg"} <= line.keys()


@pytest.mark.parametrize("every", [0, -1])
def test_nonpositive_interval_does_not_crash(tmp_path: Path, every: int) -> None:
    log, _ = make(tmp_path, every=every)
    assert log.append("a") is not None
