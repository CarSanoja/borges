from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.runs.events import Event
from borges.runs.store import RunStore


def event(run_id: str, seq: int, event_type: str = "stage") -> Event:
    return Event(seq=seq, ts=float(seq), run_id=run_id, type=event_type, data={"n": seq})


def test_create_writes_meta_and_empty_log(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs")
    store.create("r_1", {"title": "t"})
    assert store.exists("r_1")
    assert json.loads((tmp_path / "runs" / "r_1" / "meta.json").read_text())["run_id"] == "r_1"
    assert (tmp_path / "runs" / "r_1" / "events.jsonl").read_text() == ""
    assert store.events("r_1") == []


def test_append_and_read_back_in_order(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    store.create("r_1", {})
    for seq in (1, 2, 3):
        store.append(event("r_1", seq))
    lines = (tmp_path / "r_1" / "events.jsonl").read_text().splitlines()
    assert len(lines) == 3
    assert [e.seq for e in store.events("r_1")] == [1, 2, 3]
    assert store.events("r_1")[1].data == {"n": 2}


def test_truncated_trailing_line_is_ignored(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    store.create("r_1", {})
    store.append(event("r_1", 1))
    with (tmp_path / "r_1" / "events.jsonl").open("a") as handle:
        handle.write('{"seq": 2, "ts"')
    assert [e.seq for e in store.events("r_1")] == [1]


def test_update_meta_merges_fields(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    store.create("r_1", {"title": "t", "status": "running"})
    meta = store.update_meta("r_1", status="completed", cost_usd=0.5)
    assert meta["title"] == "t" and meta["status"] == "completed"
    assert store.meta("r_1")["cost_usd"] == 0.5


def test_list_runs_newest_first_skips_invalid(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    for run_id, created in (("r_old", 1.0), ("r_new", 5.0), ("r_mid", 3.0)):
        store.create(
            run_id,
            {
                "case_id": None,
                "title": run_id,
                "status": "completed",
                "created_at": created,
                "llm": "scripted",
                "backend": "local",
                "cost_usd": 0,
                "n_universes": 2,
                "verdict": "SHIP",
                "flipped_verdict": None,
            },
        )
    store.create("r_bad", {"title": "missing fields"})
    (tmp_path / "stray").mkdir()
    assert [s.run_id for s in store.list_runs()] == ["r_new", "r_mid", "r_old"]


def test_list_runs_without_directory(tmp_path: Path) -> None:
    assert RunStore(tmp_path / "nothing").list_runs() == []


def test_unknown_and_unsafe_ids(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    assert not store.exists("missing")
    assert not store.exists("../escape")
    for call in (lambda: store.events("missing"), lambda: store.append(event("missing", 1))):
        with pytest.raises(KeyError):
            call()
    with pytest.raises(KeyError):
        store.update_meta("missing", status="x")


def test_snapshot_folds_events(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    store.create("r_1", {})
    store.append(
        Event(
            seq=1, ts=1.0, run_id="r_1", type="stage", data={"name": "planning", "status": "done"}
        )
    )
    snapshot = store.snapshot("r_1")
    assert snapshot.run_id == "r_1"
    assert snapshot.stages == {"planning": "done"}
    assert snapshot.last_seq == 1
    with pytest.raises(KeyError):
        store.snapshot("missing")


def test_fail_interrupted_keeps_an_existing_terminal_pair(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    store.create("r_1", {"status": "running"})
    store.append(event("r_1", 1, "run.finished"))
    store.fail_interrupted("r_1")
    assert [e.seq for e in store.events("r_1")] == [1]
    assert store.meta("r_1")["status"] == "failed"
