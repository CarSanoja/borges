from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.cases.recording_stamp import RecordingStamp, stamp_from_meta

CASES = Path(__file__).resolve().parents[2] / "cases"
FOLDERS = sorted(CASES.glob("*/recorded-live"))


def counts(folder: Path) -> tuple[int, int]:
    started: set[str] = set()
    status: dict[str, str] = {}
    for line in (folder / "events.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["type"] == "universe.started":
            started.add(event["data"]["universe"]["id"])
        elif event["type"] == "universe.finished":
            universe = event["data"]["universe"]
            status[universe["id"]] = universe["status"]
    return len(started), sum(1 for s in status.values() if s == "failed")


def test_the_committed_recordings_are_found() -> None:
    assert len(FOLDERS) >= 6


@pytest.mark.parametrize("folder", FOLDERS, ids=lambda f: f.parent.name)
def test_recording_json_matches_its_events(folder: Path) -> None:
    stamp = json.loads((folder / "recording.json").read_text(encoding="utf-8"))
    started, failed = counts(folder)
    assert stamp["n_universes"] == started
    assert stamp["n_failed"] == failed


def test_the_stamp_carries_failures_from_the_run_meta() -> None:
    stamp = stamp_from_meta({"n_universes": 35, "n_failed": 6}, "r", "c", None, None)
    assert isinstance(stamp, RecordingStamp)
    assert (stamp.n_universes, stamp.n_failed) == (35, 6)
