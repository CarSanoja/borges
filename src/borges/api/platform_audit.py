from __future__ import annotations

import json
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


TAIL_BYTES = 262_144
DENIAL_KINDS = ("identity.access", "armor.screen", "policy.run")


def recent_denials(settings: Settings, limit: int = 5) -> list[dict[str, Any]]:
    path = global_audit_path(settings)
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - TAIL_BYTES))
            tail = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    found: list[dict[str, Any]] = []
    for line in reversed(tail.splitlines()):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if record.get("decision") != "deny" or record.get("kind") not in DENIAL_KINDS:
            continue
        data = record.get("data") or {}
        found.append(
            {
                "seq": record.get("seq"),
                "ts": record.get("ts"),
                "kind": record.get("kind"),
                "principal": record.get("principal"),
                "route": data.get("route"),
                "reason": record.get("reason"),
            }
        )
        if len(found) >= limit:
            break
    return found
