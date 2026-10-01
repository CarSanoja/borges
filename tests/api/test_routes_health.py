from __future__ import annotations

import json

import httpx

from borges.api.app import create_app
from borges.config import Settings


def client_for(settings: Settings) -> httpx.AsyncClient:
    app = create_app(settings=settings)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def test_health_defaults(tmp_path) -> None:
    settings = Settings(borges_home=tmp_path, nebius_api_key=None)
    async with client_for(settings) as client:
        body = (await client.get("/api/health")).json()
    assert body["status"] == "ok"
    assert body["llm"] == "scripted"
    assert body["llm_live_available"] is False
    assert body["spend_usd"] == 0
    assert body["spend_cap_usd"] == settings.borges_spend_cap_usd


async def test_health_reads_spend_and_key(tmp_path) -> None:
    (tmp_path / "spend.json").write_text(json.dumps({"total_usd": 1.25}))
    settings = Settings(borges_home=tmp_path, nebius_api_key="k")
    async with client_for(settings) as client:
        body = (await client.get("/api/health")).json()
    assert body["spend_usd"] == 1.25
    assert body["llm_live_available"] is True


async def test_health_tolerates_corrupt_spend(tmp_path) -> None:
    (tmp_path / "spend.json").write_text("{nope")
    async with client_for(Settings(borges_home=tmp_path)) as client:
        assert (await client.get("/api/health")).json()["spend_usd"] == 0
