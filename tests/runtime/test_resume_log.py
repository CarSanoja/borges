from __future__ import annotations

from borges.runs.events import Event
from borges.runs.store import RunStore
from borges.runtime.resume_log import NEVER_REPLAYED, replayable, rewind_events
from borges.runtime.universe_checkpoint import RestoredUniverses


def event(seq: int, kind: str, **data) -> Event:
    return Event(seq=seq, ts=float(seq), run_id="r1", type=kind, data=data)


def universe_event(seq: int, kind: str, universe_id: str) -> Event:
    return event(seq, kind, universe={"id": universe_id})


def restored(*ids: str, checkpoints: list[str] | None = None, root: str = "cp_root"):
    value = RestoredUniverses()
    for index, universe_id in enumerate(ids):
        kind = "baseline" if index == 0 else "single"
        value.payloads[universe_id] = {
            "universe": {"id": universe_id, "kind": kind, "checkpoints": checkpoints or []},
            "root_id": root,
        }
        value.order.append(universe_id)
    return value


def seeded(tmp_path, events: list[Event]) -> RunStore:
    store = RunStore(tmp_path)
    store.create("r1", {"status": "running"})
    for item in events:
        store.append(item)
    return store


def test_unfinished_universes_and_orphan_checkpoints_are_dropped(tmp_path) -> None:
    store = seeded(
        tmp_path,
        [
            event(1, "run.started"),
            event(2, "stage", name="coding", status="done", detail=""),
            event(3, "checkpoint.created", checkpoint_id="cp_root", parent_id=None),
            universe_event(4, "universe.started", "u_a"),
            event(5, "checkpoint.created", checkpoint_id="cp_1", parent_id="cp_root"),
            universe_event(6, "universe.finished", "u_a"),
            universe_event(7, "universe.started", "u_b"),
            event(8, "checkpoint.created", checkpoint_id="cp_orphan", parent_id="cp_root"),
        ],
    )
    kept, dropped = rewind_events(store, "r1", restored("u_a", checkpoints=["cp_1"]))
    assert [e.seq for e in kept] == [1, 2, 3, 4, 5, 6]
    assert dropped == 2
    assert [e.seq for e in store.events("r1")] == [1, 2, 3, 4, 5, 6]


def test_terminal_events_are_dropped_so_a_failed_run_can_resume(tmp_path) -> None:
    store = seeded(
        tmp_path,
        [
            event(1, "run.started"),
            event(2, "run.failed", error="boom"),
            event(3, "run.finished", status="failed", elapsed_s=1.0),
        ],
    )
    kept, dropped = rewind_events(store, "r1", RestoredUniverses())
    assert [e.type for e in kept] == ["run.started"] and dropped == 2


def test_without_restored_universes_the_old_search_events_go(tmp_path) -> None:
    store = seeded(
        tmp_path,
        [
            event(1, "run.started"),
            event(2, "checkpoint.created", checkpoint_id="cp_root", parent_id=None),
            universe_event(3, "universe.started", "u_a"),
        ],
    )
    kept, _ = rewind_events(store, "r1", RestoredUniverses())
    assert [e.type for e in kept] == ["run.started"]


def test_an_untouched_log_is_not_rewritten(tmp_path) -> None:
    store = seeded(tmp_path, [event(1, "run.started"), event(2, "plan.ready")])
    before = (tmp_path / "r1" / "events.jsonl").stat().st_mtime_ns
    kept, dropped = rewind_events(store, "r1", RestoredUniverses())
    assert dropped == 0 and len(kept) == 2
    assert (tmp_path / "r1" / "events.jsonl").stat().st_mtime_ns == before


def test_replayable_leaves_out_what_is_never_replayed() -> None:
    events = [event(1, kind) for kind in ("run.started", "usage", "stage", "plan.ready")]
    assert [e.type for e in replayable(events)] == ["stage", "plan.ready"]
    assert {"universe.started", "universe.finished", "checkpoint.created"} <= NEVER_REPLAYED
