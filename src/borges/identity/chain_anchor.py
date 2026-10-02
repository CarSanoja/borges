from __future__ import annotations

from pathlib import Path
from typing import Any

from borges.telemetry.audit_anchor import (
    AnchorConfig,
    anchor_problem,
    read_anchors,
    write_anchor,
)

KEY_NAME = "the store key"


def anchor_stamp(path: Path | None) -> tuple[int, int] | None:
    if path is None:
        return None
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    return info.st_mtime_ns, info.st_size


def anchor_failure(
    path: Path, anchor_key: str | None, events: list[dict[str, Any]], keyed: bool
) -> tuple[int, str] | None:
    try:
        anchors = read_anchors(path)
    except ValueError as exc:
        return 0, f"the anchor file is unreadable: {exc}"
    if not anchors:
        if keyed and events:
            return len(events), "the anchor file is missing or empty although the store has records"
        return None
    problem = anchor_problem(anchors, anchor_key, KEY_NAME)
    if problem:
        return 0, problem
    last = anchors[-1]
    if len(events) < last.count:
        return (
            len(events) + 1,
            f"the chain has {len(events)} records but the anchor attests {last.count}: "
            "the tail was truncated",
        )
    if events[last.count - 1].get("hash") != last.head_hash:
        return last.count, f"record {last.count} does not match the anchored head: chain diverges"
    return None


def record_anchor(path: Path, anchor_key: str | None, count: int, head_hash: str) -> None:
    write_anchor(AnchorConfig(path, anchor_key, 1), count, head_hash)
