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
    body = response.json()
    assert body["reproduce_command"] == (
        f"borges reproduce --case checkout_ab --universe {flip['universe_id']}"
    )
    assert body["reproduce_kind"] == "case"
    assert body["script_url"] == f"/api/runs/{run_id}/universes/{flip['universe_id']}/script"
    assert unknown.status_code == 404
    assert no_run.status_code == 404


async def test_recorded_universe_script_is_one_runnable_file(tmp_path) -> None:
    http, registry = client(tmp_path)
    events = registry.recording("red_cards")
    run_id = events[0].run_id
    flip = next(e for e in events if e.type == "flip.verified").data["flip"]
    url = f"/api/runs/{run_id}/universes/{flip['universe_id']}/script"
    async with http:
        response = await http.get(url)
        missing = await http.get(f"/api/runs/{run_id}/universes/u_missing/script")
        no_run = await http.get("/api/runs/r_nope/universes/u1/script")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert f"borges_{run_id}_{flip['universe_id']}.py" in response.headers["content-disposition"]
    compile(response.text, "script.py", "exec")
    assert "--data" in response.text
    assert "def estimate(" in response.text
    assert missing.status_code == 404
    assert no_run.status_code == 404


async def test_script_reproduces_the_recorded_estimate_when_run(tmp_path) -> None:
    import asyncio
    import subprocess
    import sys

    http, registry = client(tmp_path)
    events = registry.recording("checkout_ab")
    run_id = events[0].run_id
    flip = next(e for e in events if e.type == "flip.verified").data["flip"]
    async with http:
        response = await http.get(f"/api/runs/{run_id}/universes/{flip['universe_id']}/script")
    script = tmp_path / "universe.py"
    script.write_text(response.text)
    data = REPO_ROOT / "cases" / "checkout_ab" / "data.parquet"
    proc = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, str(script), "--data", str(data)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    assert f"verdict: {flip['flipped_verdict']}" in proc.stdout
    assert f"estimate {flip['flipped_result']['estimate']:.4f}" in proc.stdout
