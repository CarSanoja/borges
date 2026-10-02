from __future__ import annotations

from pathlib import Path

from borges.telemetry.audit_anchor import (
    anchor_path_for,
    anchor_problem,
    hashes_at,
    read_anchors,
)
from borges.telemetry.audit_verify import ChainReport, verify_chain


def _fail(report: ChainReport, reason: str, seq: int | None = None) -> ChainReport:
    return report.model_copy(update={"ok": False, "reason": reason, "broken_seq": seq})


def verify_global(log_path: Path, key: str | None, anchor_path: Path | None = None) -> ChainReport:
    report = verify_chain(log_path)
    if report.exists and not report.ok:
        return report
    target = anchor_path or anchor_path_for(log_path)
    try:
        anchors = read_anchors(target)
    except ValueError as exc:
        return _fail(report, f"anchor file unreadable: {exc}")
    if not anchors:
        return report
    if not report.exists:
        return _fail(report, "the log is missing but an anchor attests it existed")
    problem = anchor_problem(anchors, key)
    if problem is not None:
        return _fail(report, problem)
    wanted = {anchor.count for anchor in anchors}
    found, total = hashes_at(log_path, wanted)
    latest = anchors[-1]
    if total < latest.count:
        return _fail(
            report,
            f"log holds {total} records but the latest anchor attests {latest.count} "
            "(tail truncated?)",
            total + 1,
        )
    for anchor in anchors:
        if found.get(anchor.count) != anchor.head_hash:
            return _fail(
                report,
                f"record {anchor.count} does not match its anchored hash (history rewritten?)",
                anchor.count,
            )
    return report.model_copy(update={"anchored": latest.count})
