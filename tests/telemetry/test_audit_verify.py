from __future__ import annotations

import json
from pathlib import Path

from borges.telemetry.audit_log import AuditLog
from borges.telemetry.audit_verify import read_records, verify_chain


def make_log(path: Path, count: int = 5) -> AuditLog:
    log = AuditLog(path)
    for index in range(count):
        log.append("model.call", run_id="r", data={"index": index, "tokens_in": 10 * index})
    return log


def rewrite(path: Path, mutate) -> None:
    lines = path.read_text().splitlines()
    mutate(lines)
    path.write_text("\n".join(lines) + "\n")


def test_intact_chain_verifies(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    make_log(path)
    report = verify_chain(path)
    assert report.ok and report.records == 5 and report.broken_seq is None
    assert len(read_records(path)) == 5


def test_missing_log_is_reported_not_broken(tmp_path: Path) -> None:
    report = verify_chain(tmp_path / "none.jsonl")
    assert report.exists is False and report.ok is True and report.records == 0


def test_tampered_record_is_detected_at_its_seq(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    make_log(path)

    def tamper(lines: list[str]) -> None:
        record = json.loads(lines[2])
        record["data"]["tokens_in"] = 999999
        lines[2] = json.dumps(record)

    rewrite(path, tamper)
    report = verify_chain(path)
    assert not report.ok
    assert report.broken_seq == 3 and report.broken_line == 3
    assert report.records == 2
    assert "hash" in (report.reason or "")


def test_tamper_with_recomputed_hash_breaks_the_next_link(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    make_log(path)

    def forge(lines: list[str]) -> None:
        from borges.telemetry.audit_record import AuditRecord

        record = AuditRecord.model_validate(json.loads(lines[1]))
        record.data["index"] = 42
        lines[1] = record.seal().line()

    rewrite(path, forge)
    report = verify_chain(path)
    assert not report.ok and report.broken_seq == 3
    assert "prev_hash" in (report.reason or "")


def test_deleted_record_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    make_log(path)
    rewrite(path, lambda lines: lines.pop(1))
    report = verify_chain(path)
    assert not report.ok and report.broken_seq == 3
    assert "seq" in (report.reason or "")


def test_garbage_line_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    make_log(path, 2)
    rewrite(path, lambda lines: lines.append("not json"))
    report = verify_chain(path)
    assert not report.ok and report.broken_line == 3 and report.records == 2
