from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from borges.config import REPO_ROOT
from tests.api.test_routes_runtime import BODY, Env

pytestmark = pytest.mark.timeout(90)

ABSOLUTE = re.compile(
    r"(?:^|[\s=:\"'(])(/(?:Users|home|private|tmp|var|opt|etc|root|mnt|srv)/|[A-Za-z]:\\)"
)


@pytest.fixture
def env(tmp_path, monkeypatch) -> Env:
    return Env(tmp_path, monkeypatch)


def strings(node: Any):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield str(key)
            yield from strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from strings(value)


async def test_no_public_endpoint_returns_an_absolute_filesystem_path(
    env: Env, tmp_path: Path
) -> None:
    async with env.client() as client:
        run_id = (await client.post("/api/runs", json=BODY)).json()["run_id"]
        await env.runtime.drain(30)
        cases = (await client.get("/api/cases")).json()
        agents = (await client.get("/api/agents")).json()["agents"]
        urls = [
            "/api/health",
            "/api/me",
            "/api/platform",
            "/api/policy",
            "/api/cases",
            "/api/agents",
            "/api/runs",
            "/api/memory",
            f"/api/runs/{run_id}",
            f"/api/runs/{run_id}/trace",
            f"/api/runs/{run_id}/audit",
        ]
        urls += [f"/api/cases/{c['id']}" for c in cases]
        urls += [f"/api/cases/{c['id']}/recording" for c in cases if c.get("has_recording")]
        urls += [f"/api/agents/{a['agent_id']}" for a in agents[:3] if "agent_id" in a]
        checked = 0
        for url in urls:
            response = await client.get(url)
            if response.status_code != 200:
                continue
            checked += 1
            for text in strings(response.json()):
                assert str(tmp_path) not in text, (url, text[:200])
                assert str(REPO_ROOT) not in text, (url, text[:200])
                assert not ABSOLUTE.search(text), (url, text[:200])
        assert checked >= 8
        audit = (await client.get(f"/api/runs/{run_id}/audit")).json()
        assert audit["chain"]["path"] == f"{run_id}/audit.jsonl"
        assert audit["records"]
    await env.runtime.stop()
