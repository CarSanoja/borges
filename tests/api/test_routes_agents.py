from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from borges.api.app import create_app
from borges.cases.registry import CaseRegistry
from borges.config import REPO_ROOT, Settings


@pytest.fixture
def client(tmp_path: Path) -> httpx.AsyncClient:
    settings = Settings(
        _env_file=None,
        borges_home=tmp_path / "home",
        borges_runs_dir=tmp_path / "runs",
        borges_cases_dir=REPO_ROOT / "cases",
    )
    app = create_app(
        settings=settings,
        orchestrator=object(),
        registry=CaseRegistry(settings.borges_cases_dir),
        store=object(),
        bus=object(),
    )
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def test_catalog_lists_agents_and_templates(client: httpx.AsyncClient) -> None:
    async with client:
        body = (await client.get("/api/agents")).json()
    assert len(body["agents"]) == 12 and body["summary"]["by_approval"] == {"approved": 12}
    judge = next(a for a in body["agents"] if a["agent_id"] == "judge")
    assert judge["principal"] == "agent://borges/judge" and judge["version"] == "1.0.0"
    ids = {t["id"] for t in body["templates"]}
    assert {"checkout_ab", "red_cards"} <= ids
    template = next(t for t in body["templates"] if t["id"] == "checkout_ab")
    assert {"title", "owner", "metric", "decision_rule"} <= template.keys()


async def test_catalog_filters(client: httpx.AsyncClient) -> None:
    async with client:
        shadow = (await client.get("/api/agents", params={"lifecycle": "shadow"})).json()
        assurance = await client.get("/api/agents", params={"department": "analysis-assurance"})
        sandbox = (await client.get("/api/agents", params={"capability": "sandbox.exec"})).json()
    assert shadow["agents"] == []
    assert len(assurance.json()["agents"]) == 5
    assert {a["agent_id"] for a in sandbox["agents"]} >= {"harness", "verifier"}
    assert shadow["summary"]["total"] == 12


async def test_agent_detail_has_history(client: httpx.AsyncClient) -> None:
    async with client:
        body = (await client.get("/api/agents/judge")).json()
        missing = await client.get("/api/agents/ghost")
    assert body["descriptor"]["field_sources"]["prompt_sha"] == "prompt_text"
    assert [v["version"] for v in body["versions"]] == ["1.0.0"]
    assert missing.status_code == 404


async def test_version_endpoint(client: httpx.AsyncClient) -> None:
    async with client:
        found = await client.get("/api/agents/judge/versions/1.0.0")
        missing = await client.get("/api/agents/judge/versions/9.0.0")
    assert found.json()["state"] == "approved" and found.json()["history"]
    assert missing.status_code == 404
