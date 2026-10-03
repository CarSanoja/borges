from __future__ import annotations

from pathlib import Path
from typing import Any

from borges.config import Settings
from borges.telemetry.audit_anchor import anchor_path_for
from borges.telemetry.audit_global_verify import verify_global
from borges.telemetry.run_telemetry import global_audit_path

_CACHE: dict[tuple[Any, ...], dict[str, Any]] = {}


def _stamp(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return stat.st_size, stat.st_mtime_ns


def global_chain(settings: Settings) -> dict[str, Any]:
    path = global_audit_path(settings)
    key = (
        str(path),
        _stamp(path),
        _stamp(anchor_path_for(path)),
        bool(settings.borges_audit_anchor_key),
    )
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    report = verify_global(path, settings.borges_audit_anchor_key)
    result = {
        "exists": report.exists,
        "ok": report.ok,
        "records": report.records,
        "anchor_present": report.anchored is not None,
        "anchored_records": report.anchored,
        "signed_anchor": bool(settings.borges_audit_anchor_key),
        "reason": report.reason,
    }
    _CACHE.clear()
    _CACHE[key] = result
    return result
