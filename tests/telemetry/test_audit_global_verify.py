from __future__ import annotations

from pathlib import Path

from borges.telemetry.audit_anchor import AnchorConfig, anchor_path_for
from borges.telemetry.audit_global_verify import verify_global
from borges.telemetry.audit_log import AuditLog


def build(tmp_path: Path, n: int, key: str | None = None, every: int = 2):
    path = tmp_path / "global.jsonl"
    log = AuditLog(path, AnchorConfig(anchor_path_for(path), key, every))
    for index in range(n):
        log.append(f"k{index}")
    return path, log


def test_intact_log_verifies_against_its_anchor(tmp_path: Path) -> None:
    path, _ = build(tmp_path, 5)
    report = verify_global(path, None)
    assert report.ok and report.records == 5 and report.anchored == 4


def test_tail_truncation_is_detected(tmp_path: Path) -> None:
    path, _ = build(tmp_path, 6)
    lines = path.read_text().splitlines()
    path.write_text("\n".join(lines[:3]) + "\n")
    plain = AuditLog(path)
    assert plain.append("later") is not None
    report = verify_global(path, None)
    assert not report.ok
    assert report.reason is not None and "anchor" in report.reason


def test_truncation_that_leaves_a_valid_chain_is_still_detected(tmp_path: Path) -> None:
    path, _ = build(tmp_path, 6)
    lines = path.read_text().splitlines()
    path.write_text("\n".join(lines[:4]) + "\n")
    report = verify_global(path, None)
    assert not report.ok and "truncated" in (report.reason or "")
    assert report.broken_seq == 5


def test_deleted_log_with_surviving_anchor_is_detected(tmp_path: Path) -> None:
    path, _ = build(tmp_path, 4)
    path.unlink()
    report = verify_global(path, None)
    assert not report.ok and "missing" in (report.reason or "")


def test_rewritten_history_is_detected_by_the_anchor(tmp_path: Path) -> None:
    path, _ = build(tmp_path, 4)
    other = tmp_path / "other.jsonl"
    forged = AuditLog(other)
    for index in range(4):
        forged.append(f"forged{index}")
    path.write_text(other.read_text())
    report = verify_global(path, None)
    assert not report.ok and "anchored hash" in (report.reason or "")


def test_signed_anchors_need_the_key_and_detect_forgery(tmp_path: Path) -> None:
    path, _ = build(tmp_path, 4, key="secret")
    assert verify_global(path, "secret").ok
    assert "BORGES_AUDIT_ANCHOR_KEY" in (verify_global(path, None).reason or "")
    assert "signature" in (verify_global(path, "other").reason or "")


def test_removed_middle_anchor_is_detected(tmp_path: Path) -> None:
    path, _ = build(tmp_path, 6)
    anchor_file = anchor_path_for(path)
    lines = anchor_file.read_text().splitlines()
    anchor_file.write_text("\n".join([lines[0], lines[2]]) + "\n")
    assert "removed" in (verify_global(path, None).reason or "")


def test_unanchored_log_still_verifies_its_chain(tmp_path: Path) -> None:
    path = tmp_path / "global.jsonl"
    AuditLog(path).append("a")
    report = verify_global(path, None)
    assert report.ok and report.anchored is None


def test_broken_chain_is_reported_first(tmp_path: Path) -> None:
    path, _ = build(tmp_path, 4)
    path.write_text(path.read_text().replace("k1", "kX"))
    assert not verify_global(path, None).ok
