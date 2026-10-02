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


async def test_health_unavailable_reasons(tmp_path) -> None:
    async with client_for(Settings(borges_home=tmp_path, nebius_api_key=None)) as client:
        assert (await client.get("/api/health")).json()["live_unavailable_reason"] == "no_key"
    (tmp_path / "spend.json").write_text(json.dumps({"total_usd": 5.0}))
    settings = Settings(borges_home=tmp_path, nebius_api_key="k", borges_spend_cap_usd=5.0)
    async with client_for(settings) as client:
        body = (await client.get("/api/health")).json()
    assert body["live_unavailable_reason"] == "budget_spent"
    assert body["llm_live_available"] is False


async def test_health_live_available_has_no_reason(tmp_path) -> None:
    async with client_for(Settings(borges_home=tmp_path, nebius_api_key="k")) as client:
        body = (await client.get("/api/health")).json()
    assert body["live_unavailable_reason"] is None
    assert body["llm_live_available"] is True


async def _uploads(settings: Settings) -> dict:
    async with client_for(settings) as client:
        return (await client.get("/api/health")).json()


async def test_uploads_unavailable_without_a_key(tmp_path) -> None:
    body = await _uploads(Settings(_env_file=None, borges_home=tmp_path, nebius_api_key=None))
    assert body["uploads_available"] is False
    assert "NEBIUS_API_KEY" in body["uploads_unavailable_reason"]


async def test_uploads_unavailable_on_untrusted_local_backend(tmp_path) -> None:
    settings = Settings(_env_file=None, borges_home=tmp_path, nebius_api_key="k")
    body = await _uploads(settings)
    assert body["uploads_available"] is False
    assert "BORGES_ALLOW_UNTRUSTED_LOCAL" in body["uploads_unavailable_reason"]


async def test_uploads_available_with_a_key_and_a_trusted_backend(tmp_path) -> None:
    trusted_local = Settings(
        _env_file=None,
        borges_home=tmp_path,
        nebius_api_key="k",
        borges_allow_untrusted_local=True,
    )
    contree = Settings(
        _env_file=None, borges_home=tmp_path, nebius_api_key="k", borges_backend="contree"
    )
    for settings in (trusted_local, contree):
        body = await _uploads(settings)
        assert body["uploads_available"] is True
        assert body["uploads_unavailable_reason"] is None


async def test_uploads_unavailable_when_the_budget_is_spent(tmp_path) -> None:
    (tmp_path / "spend.json").write_text(json.dumps({"total_usd": 9.0}))
    settings = Settings(
        _env_file=None,
        borges_home=tmp_path,
        nebius_api_key="k",
        borges_backend="contree",
        borges_spend_cap_usd=5.0,
    )
    body = await _uploads(settings)
    assert body["uploads_available"] is False
    assert "budget" in body["uploads_unavailable_reason"]
