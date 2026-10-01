from __future__ import annotations

import time
from pathlib import Path

from borges.api.app import create_app
from borges.api.startup import reconcile, sweep_sandboxes
from borges.config import Settings
from borges.runs.bus import EventBus
from borges.runs.events import Event
from borges.runs.store import RunStore


def seed_running(store: RunStore, run_id: str, events: int = 2) -> None:
    store.create(
        run_id,
        {
            "case_id": None,
            "title": "t",
            "status": "running",
            "created_at": time.time(),
            "llm": "nebius",
            "backend": "local",
            "cost_usd": 0.0,
            "n_universes": 0,
            "verdict": None,
            "flipped_verdict": None,
        },
    )

    for seq in range(1, events + 1):
        store.append(
            Event(
                seq=seq,
                ts=1.0,
                run_id=run_id,
                type="stage",
                data={"name": "plan", "status": "running"},
            )
        )


def test_running_runs_without_a_task_are_failed_with_terminal_events(tmp_path: Path) -> None:
    store = RunStore(tmp_path)
    seed_running(store, "r_a")
    seed_running(store, "r_b")
    stale = store.interrupt_running({"r_b"})
    assert stale == ["r_a"]
    events = store.events("r_a")
    assert [e.type for e in events][-2:] == ["run.failed", "run.finished"]
    assert [e.seq for e in events] == [1, 2, 3, 4]
    assert events[-2].data["error"] == "interrupted by a server restart"
    assert store.meta("r_a")["status"] == "failed"
    assert store.meta("r_b")["status"] == "running"
    assert store.snapshot("r_a").status == "failed"


def test_sweep_removes_stale_sandbox_directories(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, borges_home=tmp_path)
    stale = tmp_path / "sandboxes" / "sb_dead" / "checkpoints"
    stale.mkdir(parents=True)
    (stale / "blob").write_bytes(b"x")
    sweep_sandboxes(settings)
    assert not (tmp_path / "sandboxes" / "sb_dead").exists()


def test_reconcile_with_no_sandbox_dir_is_a_noop(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs")
    reconcile(Settings(_env_file=None, borges_home=tmp_path), store, object())


async def test_lifespan_reconciles_and_awaits_shutdown(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs")
    seed_running(store, "r_zombie")
    calls: list[str] = []

    class Orch:
        tasks: dict = {}

        async def shutdown(self) -> None:
            calls.append("shutdown")

    settings = Settings(_env_file=None, borges_home=tmp_path / "home")
    app = create_app(
        settings, orchestrator=Orch(), registry=object(), store=store, bus=EventBus(store)
    )
    async with app.router.lifespan_context(app):
        assert store.meta("r_zombie")["status"] == "failed"
    assert calls == ["shutdown"]
