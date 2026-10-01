from __future__ import annotations

import httpx

from borges.api.app import create_app
from borges.cases.registry import CaseRegistry
from borges.config import REPO_ROOT, Settings
from borges.runs.bus import EventBus
from borges.runs.orchestrator import RunOrchestrator
from borges.runs.store import RunStore


def client(tmp_path) -> tuple[httpx.AsyncClient, CaseRegistry]:
    settings = Settings(
        _env_file=None,
        borges_home=tmp_path / "home",
        borges_runs_dir=tmp_path / "runs",
        borges_cases_dir=REPO_ROOT / "cases",
    )
    store = RunStore(settings.borges_runs_dir)
    registry = CaseRegistry(settings.borges_cases_dir)
    app = create_app(
        settings,
        orchestrator=RunOrchestrator(settings, store, EventBus(store), registry),
        registry=registry,
        store=store,
        bus=EventBus(store),
    )
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t"), registry


async def test_recorded_run_universe_resolves_without_a_stored_run(tmp_path) -> None:
    http, registry = client(tmp_path)
    events = registry.recording("checkout_ab")
    run_id = events[0].run_id
    flip = next(e for e in events if e.type == "flip.verified").data["flip"]
    async with http:
        response = await http.get(f"/api/runs/{run_id}/universes/{flip['universe_id']}")
        unknown = await http.get(f"/api/runs/{run_id}/universes/u_missing")
        no_run = await http.get("/api/runs/r_nope/universes/u1")
    assert response.status_code == 200
    assert response.json()["reproduce_command"] == flip["reproduce_command"]
    assert unknown.status_code == 404
    assert no_run.status_code == 404
