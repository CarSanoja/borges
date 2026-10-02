from __future__ import annotations

import json
from pathlib import Path

from borges.telemetry.audit_verify import ChainReport, verify_chain

TRUNCATED = "run log has fewer records than the global log holds for this run (tail removed?)"


def global_count_for(global_path: Path | None, run_id: str) -> int:
    if global_path is None or not Path(global_path).is_file():
        return 0
    count = 0
    for line in Path(global_path).read_text(encoding="utf-8").splitlines():
        if run_id not in line:
            continue
        try:
            if json.loads(line).get("run_id") == run_id:
                count += 1
        except ValueError:
            continue
    return count


def verify_run_chain(run_path: Path, global_path: Path | None, run_id: str) -> ChainReport:
    report = verify_chain(run_path)
    if not report.exists or not report.ok:
        return report
    expected = global_count_for(global_path, run_id)
    if report.records < expected:
        return report.model_copy(
            update={
                "ok": False,
                "broken_seq": report.records + 1,
                "broken_line": report.records + 1,
                "reason": TRUNCATED,
            }
        )
    return report
