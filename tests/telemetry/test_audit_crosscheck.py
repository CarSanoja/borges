from __future__ import annotations

from pathlib import Path

from borges.telemetry.audit_crosscheck import TRUNCATED, verify_run_chain
from borges.telemetry.audit_log import AuditLog


def _two_logs(tmp_path: Path) -> tuple[Path, Path]:
    run, glob = AuditLog(tmp_path / "run.jsonl"), AuditLog(tmp_path / "global.jsonl")
    for kind in ("a", "b", "c"):
        run.append(kind, run_id="r1")
        glob.append(kind, run_id="r1")
    glob.append("other", run_id="r2")
    return tmp_path / "run.jsonl", tmp_path / "global.jsonl"


def test_intact_logs_verify(tmp_path: Path) -> None:
    run, glob = _two_logs(tmp_path)
    report = verify_run_chain(run, glob, "r1")
    assert report.ok and report.records == 3


def test_removing_the_run_tail_is_caught_by_the_global_log(tmp_path: Path) -> None:
    run, glob = _two_logs(tmp_path)
    lines = run.read_text().splitlines()
    run.write_text("\n".join(lines[:-1]) + "\n")
    report = verify_run_chain(run, glob, "r1")
    assert not report.ok and report.reason == TRUNCATED and report.broken_seq == 3


def test_a_missing_global_log_is_not_an_error(tmp_path: Path) -> None:
    run, _ = _two_logs(tmp_path)
    assert verify_run_chain(run, tmp_path / "none.jsonl", "r1").ok
    assert verify_run_chain(run, None, "r1").ok
