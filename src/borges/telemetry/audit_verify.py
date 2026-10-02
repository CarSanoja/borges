from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from borges.telemetry.audit_record import GENESIS_HASH, AuditRecord


class ChainReport(BaseModel):
    path: str
    exists: bool
    ok: bool
    records: int = 0
    head_hash: str = GENESIS_HASH
    broken_seq: int | None = None
    broken_line: int | None = None
    reason: str | None = None


def _break(report: ChainReport, line: int, seq: int | None, reason: str) -> ChainReport:
    return report.model_copy(
        update={"ok": False, "broken_line": line, "broken_seq": seq, "reason": reason}
    )


def verify_chain(path: Path) -> ChainReport:
    path = Path(path)
    report = ChainReport(path=str(path), exists=path.is_file(), ok=True)
    if not report.exists:
        return report
    prev_hash, expected_seq, count = GENESIS_HASH, 1, 0
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            record = AuditRecord.model_validate(json.loads(raw))
        except ValueError as exc:
            return _break(
                report.model_copy(update={"records": count}),
                number,
                None,
                f"unreadable record: {exc}",
            )
        stamped = report.model_copy(update={"records": count})
        if record.seq != expected_seq:
            return _break(
                stamped, number, record.seq, f"expected seq {expected_seq}, found {record.seq}"
            )
        if record.prev_hash != prev_hash:
            return _break(
                stamped, number, record.seq, "prev_hash does not match the previous record"
            )
        if record.seal().hash != record.hash:
            return _break(stamped, number, record.seq, "record hash does not match its content")
        prev_hash, expected_seq, count = record.hash, expected_seq + 1, count + 1
    return report.model_copy(update={"records": count, "head_hash": prev_hash})


def read_records(path: Path) -> list[AuditRecord]:
    records: list[AuditRecord] = []
    if not Path(path).is_file():
        return records
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            records.append(AuditRecord.model_validate(json.loads(raw)))
        except ValueError:
            continue
    return records
