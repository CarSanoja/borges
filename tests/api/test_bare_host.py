from __future__ import annotations

from pathlib import Path

import httpx

from borges.api.app import create_app
from borges.api.live_rules import BARE_HOST_MESSAGE
from borges.config import Settings
from tests.api.test_routes_runs import Env

LIVE = {"case_id": "a", "llm": "nebius"}


async def test_a_live_run_on_the_bare_host_is_refused(tmp_path: Path) -> None:
    env = Env(tmp_path, key="k", borges_isolated_host=False)
    async with env.client() as client:
        response = await client.post("/api/runs", json=LIVE)
    assert response.status_code == 400
    assert response.json()["detail"] == BARE_HOST_MESSAGE
    assert env.orchestrator.calls == []


async def test_a_scripted_run_on_the_bare_host_still_runs(tmp_path: Path) -> None:
    env = Env(tmp_path, key="k", borges_isolated_host=False)
    async with env.client() as client:
        response = await client.post("/api/runs", json={"case_id": "a"})
    assert response.status_code == 202


async def test_sandboxes_a_container_or_an_explicit_opt_in_lift_the_refusal(
    tmp_path: Path,
) -> None:
    for i, fields in enumerate(
        (
            {"borges_backend": "contree"},
            {"borges_isolated_host": True},
            {"borges_allow_untrusted_local": True},
        )
    ):
        home = tmp_path / str(i)
        home.mkdir()
        env = Env(home, key="k", **{"borges_isolated_host": False, **fields})
        async with env.client() as client:
            response = await client.post("/api/runs", json=LIVE)
        assert response.status_code == 202, fields


async def test_health_says_why_live_runs_are_off_on_the_bare_host(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, borges_home=tmp_path, nebius_api_key="k")
    transport = httpx.ASGITransport(app=create_app(settings=settings))
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        body = (await client.get("/api/health")).json()
    assert body["llm_live_available"] is False
    assert body["live_unavailable_reason"] == "bare_host"
