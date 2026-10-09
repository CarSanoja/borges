from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from borges.api.app import create_app
from borges.cases.registry import CaseRegistry
from borges.config import REPO_ROOT, Settings
from tests.fleet.seed_versions import seed_version, seed_versions
from tests.identity.keys import bearer, make_key


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
    assert judge["principal"] == "agent://borges/judge" and judge["version"] == seed_version(
        "judge"
    )
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
    assert [v["version"] for v in body["versions"]] == seed_versions("judge")
    assert missing.status_code == 404


async def test_version_endpoint(client: httpx.AsyncClient) -> None:
    async with client:
        found = await client.get("/api/agents/judge/versions/1.0.0")
        missing = await client.get("/api/agents/judge/versions/9.0.0")
    assert found.json()["state"] == "approved" and found.json()["history"]
    assert missing.status_code == 404


async def test_anonymous_cannot_publish_or_approve(client: httpx.AsyncClient) -> None:
    async with client:
        assert (await client.post("/api/agents/publish")).status_code == 403
        approve = await client.post("/api/agents/judge/versions/1.1.0/approve")
    assert approve.status_code == 403


def with_key(tmp_path: Path, scopes: str, name: str) -> tuple[httpx.AsyncClient, Settings]:
    settings = Settings(
        _env_file=None,
        borges_home=tmp_path / "home",
        borges_runs_dir=tmp_path / "runs",
        borges_cases_dir=REPO_ROOT / "cases",
        borges_registry_four_eyes=True,
    )
    app = create_app(
        settings=settings,
        orchestrator=object(),
        registry=CaseRegistry(settings.borges_cases_dir),
        store=object(),
        bus=object(),
    )
    headers = bearer(make_key(settings, scopes, name))
    return (
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://t", headers=headers
        ),
        settings,
    )


async def test_publish_is_a_noop_when_the_seed_is_current(tmp_path: Path) -> None:
    client, _ = with_key(tmp_path, "registry:publish", "pub")
    async with client:
        response = await client.post("/api/agents/publish", json={"message": "nothing"})
    assert response.status_code == 200 and response.json() == []


async def test_approving_an_approved_version_is_409(tmp_path: Path) -> None:
    client, _ = with_key(tmp_path, "registry:approve", "bob")
    async with client:
        again = await client.post("/api/agents/judge/versions/1.1.0/approve")
        unknown = await client.post("/api/agents/judge/versions/9.9.9/approve")
    assert again.status_code == 409 and unknown.status_code == 404


async def test_four_eyes_over_http(tmp_path: Path) -> None:
    from borges.fleet.locations import open_store

    client, settings = with_key(tmp_path, "registry:approve", "alice")
    store = open_store(settings)
    store.publish("judge", "9.0.0", "sha-new", {}, "major", "x", "caller://alice")
    store.publish("coder", "9.0.0", "sha-new", {}, "major", "x", "caller://zed")
    async with client:
        own = await client.post("/api/agents/judge/versions/9.0.0/approve")
        other = await client.post("/api/agents/coder/versions/9.0.0/approve", json={"reason": "ok"})
    assert own.status_code == 403 and "four-eyes" in own.json()["detail"]
    assert other.status_code == 200
    assert other.json()["history"][-1]["by"] == "caller://alice"
