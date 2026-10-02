from __future__ import annotations

from pathlib import Path

import httpx

from borges.api.app import create_app
from borges.cases.registry import CaseRegistry
from borges.config import Settings
from borges.runs.bus import EventBus
from borges.runs.orchestrator import RunOrchestrator
from borges.runs.store import RunStore
from tests.live_cases import LIVE_FLIP_UNIVERSE, LIVE_RUN_ID, make_cases_dir


def build_app(tmp_path: Path, frontend: Path | None = None, **flags: bool):
    cases = make_cases_dir(tmp_path, **flags)
    settings = Settings(
        _env_file=None,
        borges_home=tmp_path / "home",
        borges_runs_dir=tmp_path / "runs",
        borges_cases_dir=cases,
        **({"borges_frontend_dist": frontend} if frontend else {}),
    )
    store = RunStore(settings.borges_runs_dir)
    registry = CaseRegistry(cases)
    return create_app(
        settings,
        orchestrator=RunOrchestrator(settings, store, EventBus(store), registry),
        registry=registry,
        store=store,
        bus=EventBus(store),
    )


def client(tmp_path: Path, **flags: bool) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=build_app(tmp_path, **flags))
    return httpx.AsyncClient(transport=transport, base_url="http://t")


def run_ids(text: str) -> set[str]:
    return {
        line.split('"run_id":"')[1].split('"')[0]
        for line in text.splitlines()
        if '"run_id":"' in line
    }


async def test_default_replay_is_live_when_a_live_recording_exists(tmp_path: Path) -> None:
    async with client(tmp_path) as c:
        text = (await c.get("/api/cases/checkout_ab/recording?speed=100")).text
    assert run_ids(text) == {LIVE_RUN_ID}


async def test_scripted_source_serves_the_scripted_recording(tmp_path: Path) -> None:
    async with client(tmp_path) as c:
        response = await c.get("/api/cases/checkout_ab/recording?speed=100&source=scripted")
    assert response.status_code == 200
    assert LIVE_RUN_ID not in response.text


async def test_default_is_scripted_without_a_live_recording(tmp_path: Path) -> None:
    async with client(tmp_path, live=False) as c:
        ok = await c.get("/api/cases/checkout_ab/recording?speed=100")
        missing = await c.get("/api/cases/checkout_ab/recording?source=live")
    assert ok.status_code == 200
    assert missing.status_code == 404


async def test_missing_scripted_source_is_404_and_bad_source_is_422(tmp_path: Path) -> None:
    async with client(tmp_path, scripted=False, live_only=True) as c:
        scripted = await c.get("/api/cases/checkout_ab/recording?source=scripted")
        live = await c.get("/api/cases/checkout_ab/recording?speed=100")
        bad = await c.get("/api/cases/checkout_ab/recording?source=x")
    assert scripted.status_code == 404
    assert live.status_code == 200
    assert bad.status_code == 422


async def test_case_card_carries_the_live_summary(tmp_path: Path) -> None:
    async with client(tmp_path) as c:
        body = (await c.get("/api/cases/checkout_ab")).json()
    assert body["has_recording"] is True
    assert body["live_recording"]["llm_calls"] == 22
    assert body["live_recording"]["flip_kind"] == "direction"


async def test_universe_detail_and_script_work_for_the_live_run(tmp_path: Path) -> None:
    base = f"/api/runs/{LIVE_RUN_ID}/universes/{LIVE_FLIP_UNIVERSE}"
    async with client(tmp_path) as c:
        detail = await c.get(base)
        script = await c.get(f"{base}/script")
    assert detail.status_code == 200
    body = detail.json()
    assert body["reproduce_kind"] == "case"
    assert body["reproduce_command"].endswith(f"--universe {LIVE_FLIP_UNIVERSE} --source live")
    assert script.status_code == 200
    assert "attachment" in script.headers["content-disposition"]


async def test_scripted_universe_command_has_no_source_flag(tmp_path: Path) -> None:
    scripted = CaseRegistry(make_cases_dir(tmp_path / "x")).recording("checkout_ab")
    run_id = scripted[0].run_id
    universe = next(e.data["flip"]["universe_id"] for e in scripted if e.type == "flip.verified")
    async with client(tmp_path) as c:
        body = (await c.get(f"/api/runs/{run_id}/universes/{universe}")).json()
    assert "--source" not in body["reproduce_command"]


async def test_spa_replay_route_is_200_for_live_only_case(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>spa</html>")
    app = build_app(tmp_path, dist, scripted=False, live_only=True)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        assert (await c.get("/replay/checkout_ab")).status_code == 200
        assert (await c.get("/replay/nope")).status_code == 404
