from __future__ import annotations

import pytest

from tests.api.test_routes_runtime import BODY, Env
from tests.identity.keys import bearer, make_key

pytestmark = pytest.mark.timeout(60)


@pytest.fixture
def env(tmp_path, monkeypatch) -> Env:
    return Env(tmp_path, monkeypatch)


async def test_anonymous_callers_cannot_ask_for_a_blind_run(env: Env) -> None:
    async with env.client() as client:
        reply = await client.post("/api/runs", json={**BODY, "blind_notes": True})
        plain = await client.post("/api/runs", json=BODY)
        await env.runtime.drain(30)
    assert reply.status_code == 403
    assert "named keys" in reply.json()["detail"]
    assert plain.status_code == 202
    await env.runtime.stop()


async def test_a_named_key_can_ask_for_a_blind_run(env: Env) -> None:
    key = bearer(make_key(env.settings, "runs:create:scripted,runs:read", "alice"))
    async with env.client() as client:
        reply = await client.post("/api/runs", json={**BODY, "blind_notes": True}, headers=key)
        await env.runtime.drain(30)
    assert reply.status_code == 202
    await env.runtime.stop()
