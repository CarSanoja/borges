from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from borges.api.app import create_app
from borges.cases.registry import CaseRegistry
from borges.config import REPO_ROOT, Settings
from borges.runs.bus import EventBus
from borges.runs.orchestrator import RunOrchestrator
from borges.runs.store import RunStore

pytestmark = pytest.mark.timeout(240)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>Borges</title>")
    return Settings(
        _env_file=None,
        nebius_api_key=None,
        borges_llm="scripted",
        borges_backend="local",
        borges_home=tmp_path / "home",
        borges_runs_dir=tmp_path / "runs",
        borges_cases_dir=REPO_ROOT / "cases",
        borges_frontend_dist=dist,
    )


@pytest.fixture
def app(settings: Settings):
    store = RunStore(settings.borges_runs_dir)
    bus = EventBus(store)
    registry = CaseRegistry(settings.borges_cases_dir)
    orchestrator = RunOrchestrator(settings, store, bus, registry)
    return create_app(settings, orchestrator=orchestrator, registry=registry, store=store, bus=bus)


async def _wait_finished(client: httpx.AsyncClient, run_id: str) -> dict:
    for _ in range(400):
        snapshot = (await client.get(f"/api/runs/{run_id}")).json()
        if snapshot["status"] != "running":
            return snapshot
        await asyncio.sleep(0.5)
    raise AssertionError("run did not finish")


async def _stream_types(client: httpx.AsyncClient, run_id: str) -> list[str]:
    types: list[str] = []
    async with client.stream("GET", f"/api/runs/{run_id}/events?from_seq=0") as response:
        async for line in response.aiter_lines():
            if line.startswith("data:"):
                types.append(json.loads(line[5:])["type"])
                if types[-1] == "run.finished":
                    break
    return types


async def test_checkout_case_runs_end_to_end_through_the_api(app, settings: Settings) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://borges") as client:
        assert (await client.get("/api/health")).json()["llm_live_available"] is False
        assert "Borges" in (await client.get("/replay/checkout_ab")).text

        created = await client.post(
            "/api/runs", json={"case_id": "checkout_ab", "llm": "scripted", "backend": "local"}
        )
        assert created.status_code == 202
        run_id = created.json()["run_id"]

        snapshot = await _wait_finished(client, run_id)
        assert snapshot["status"] == "completed", snapshot["error"]
        flip = snapshot["flip"]
        assert flip["baseline_verdict"] == "SHIP"
        assert flip["flipped_verdict"] == "DON'T SHIP"
        assert [c["to_option"] for c in flip["changes"]] == ["exclude_internal"]
        assert flip["reproduced"] is True
        assert snapshot["report"]["narrative"]

        types = await _stream_types(client, run_id)
        assert types[0] == "run.started" and types[-1] == "run.finished"
        assert {"checkpoint.created", "flip.found", "flip.verified", "report.ready"} <= set(types)

        detail = (await client.get(f"/api/runs/{run_id}/universes/{flip['universe_id']}")).json()
        changed = [s["option"]["id"] for s in detail["steps"] if s["changed"]]
        assert changed == ["exclude_internal"]
        assert all(s["option"]["code"] for s in detail["steps"])
        assert all(s["checkpoint_id"] for s in detail["steps"])

    sandboxes = settings.borges_home / "sandboxes"
    assert not sandboxes.exists() or not any(sandboxes.iterdir())
