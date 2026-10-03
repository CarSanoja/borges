from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from borges.cases.git_info import current_commit, src_is_dirty

STAMP_FILE = "recording.json"
REPO_ROOT = Path(__file__).resolve().parents[3]


class RecordingStamp(BaseModel):
    run_id: str | None = None
    case_id: str | None = None
    recorded_at: str | None = None
    commit: str | None = None
    dirty: bool | None = None
    llm: str | None = None
    backend: str | None = None
    registry_sha: str | None = None
    cost_usd: float | None = None
    n_universes: int | None = None
    verdict: str | None = None
    flipped_verdict: str | None = None


def iso_utc(created_at: Any) -> str | None:
    if isinstance(created_at, bool) or not isinstance(created_at, int | float):
        return None
    stamp = datetime.fromtimestamp(created_at, tz=UTC)
    return stamp.isoformat(timespec="seconds").replace("+00:00", "Z")


def read_meta(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "meta.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def stamp_from_meta(
    meta: dict[str, Any],
    run_id: str | None,
    case_id: str | None,
    commit: str | None,
    dirty: bool | None,
) -> RecordingStamp:
    agents = meta.get("agents")
    sha = agents.get("registry_sha") if isinstance(agents, dict) else None
    return RecordingStamp(
        run_id=run_id or meta.get("run_id"),
        case_id=case_id or meta.get("case_id"),
        recorded_at=iso_utc(meta.get("created_at")),
        commit=commit,
        dirty=dirty,
        llm=meta.get("llm"),
        backend=meta.get("backend"),
        registry_sha=sha,
        cost_usd=meta.get("cost_usd"),
        n_universes=meta.get("n_universes"),
        verdict=meta.get("verdict"),
        flipped_verdict=meta.get("flipped_verdict"),
    )


def write_stamp(folder: Path, stamp: RecordingStamp) -> Path:
    target = folder / STAMP_FILE
    target.write_text(stamp.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return target


def stamp_copy(run_dir: Path, run_id: str, case_id: str, folder: Path) -> Path:
    stamp = stamp_from_meta(
        read_meta(run_dir), run_id, case_id, current_commit(REPO_ROOT), src_is_dirty(REPO_ROOT)
    )
    return write_stamp(folder, stamp)


def read_stamp(folder: Path) -> RecordingStamp | None:
    try:
        raw = json.loads((folder / STAMP_FILE).read_text(encoding="utf-8"))
        return RecordingStamp.model_validate(raw)
    except (OSError, ValueError):
        return None
