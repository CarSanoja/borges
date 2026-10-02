from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from borges.api.app import create_app
from borges.cases.registry import CaseRegistry
from borges.config import REPO_ROOT, Settings


def make_client(tmp_path: Path, policy: Path | None = None) -> httpx.AsyncClient:
    extra = {"borges_gateway_policy": policy} if policy else {}
    settings = Settings(
        _env_file=None,
        borges_home=tmp_path / "home",
        borges_runs_dir=tmp_path / "runs",
        borges_cases_dir=REPO_ROOT / "cases",
        **extra,
    )
    app = create_app(
        settings=settings,
        orchestrator=object(),
        registry=CaseRegistry(settings.borges_cases_dir),
        store=object(),
        bus=object(),
    )
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


@pytest.fixture
def client(tmp_path: Path) -> httpx.AsyncClient:
    return make_client(tmp_path)


async def test_anonymous_visitors_can_read_the_effective_policy(client: httpx.AsyncClient) -> None:
    async with client:
        response = await client.get("/api/policy")
    body = response.json()
    assert response.status_code == 200 and len(body["sha"]) == 64
    judge = body["policy"]["agents"]["judge"]
    assert judge["egress"] == "profile_only" and judge["models"]
    assert body["policy"]["sandbox"]["network"] == "none"
    assert body["policy"]["run"]["max_calls"] > 0


async def test_policy_exposes_no_credentials(client: httpx.AsyncClient) -> None:
    async with client:
        text = (await client.get("/api/policy")).text.lower()
    for word in ("api_key", "secret", "password", "bearer", "nebius_api"):
        assert word not in text


async def test_policy_sha_matches_the_agent_cards(client: httpx.AsyncClient) -> None:
    async with client:
        agents = (await client.get("/api/agents")).json()["agents"]
    judge = next(a for a in agents if a["agent_id"] == "judge")
    assert judge["policy"]["egress"] == "profile_only" and judge["policy_sha"]
    harness = next(a for a in agents if a["agent_id"] == "harness")
    assert harness["sandbox_policy"]["network"] == "none" and harness["policy"] is None
    guard = next(a for a in agents if a["agent_id"] == "code_guard")
    assert guard["policy"] is None and guard["sandbox_policy"] is None


async def test_unreadable_policy_is_a_503_not_a_default(tmp_path: Path) -> None:
    client = make_client(tmp_path, tmp_path / "missing.json")
    async with client:
        response = await client.get("/api/policy")
    assert response.status_code == 503 and "cannot be read" in response.json()["detail"]
