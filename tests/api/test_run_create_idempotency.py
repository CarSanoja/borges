from __future__ import annotations

import asyncio

import pytest

from borges.identity.principal import ANONYMOUS
from borges.runs.models import RunRequest
from tests.api.test_routes_runtime import BODY, Env
from tests.identity.keys import bearer, make_key
from tests.runtime.rig import wait_for

pytestmark = pytest.mark.timeout(60)


@pytest.fixture
def env(tmp_path, monkeypatch) -> Env:
    return Env(tmp_path, monkeypatch)


async def test_concurrent_posts_with_one_key_create_one_run(env: Env) -> None:
    headers = {"Idempotency-Key": "race"}
    async with env.client() as client:
        replies = await asyncio.gather(
            *[client.post("/api/runs", json=BODY, headers=headers) for _ in range(8)]
        )
        await env.runtime.drain(30)
    assert {r.status_code for r in replies} == {202}
    assert len({r.json()["run_id"] for r in replies}) == 1
    assert len(env.rig.store.list_runs()) == 1
    assert len(env.runtime.queue.active_run_ids()) == 0
    await env.runtime.stop()


async def test_another_anonymous_client_does_not_get_my_run_by_reusing_my_key(env: Env) -> None:
    headers = {"Idempotency-Key": "shared-key"}
    async with env.client("10.0.0.1") as one, env.client("10.0.0.2") as two:
        mine = await one.post("/api/runs", json=BODY, headers=headers)
        theirs = await two.post("/api/runs", json=BODY, headers=headers)
        await env.runtime.drain(30)
    assert mine.json()["run_id"] != theirs.json()["run_id"]
    assert "Idempotent-Replay" not in theirs.headers
    await env.runtime.stop()


async def test_another_named_principal_does_not_get_my_run_by_reusing_my_key(env: Env) -> None:
    scopes = "runs:create:scripted,runs:read"
    alice = bearer(make_key(env.settings, scopes, "alice"))
    bob = bearer(make_key(env.settings, scopes, "bob"))
    async with env.client() as client:
        a = await client.post("/api/runs", json=BODY, headers={**alice, "Idempotency-Key": "k"})
        b = await client.post("/api/runs", json=BODY, headers={**bob, "Idempotency-Key": "k"})
        await env.runtime.drain(30)
    assert a.json()["run_id"] != b.json()["run_id"]
    await env.runtime.stop()


async def test_the_runs_of_many_clients_never_exceed_the_active_cap(env: Env) -> None:
    env.scenario.hang = True
    cap = env.settings.borges_max_active_runs
    peak = 0
    for i in range(cap + 4):
        await env.runtime.submit(RunRequest(**BODY), ANONYMOUS, f"10.1.0.{i}")
    await wait_for(lambda: env.scenario.entered_plan.is_set())
    for _ in range(20):
        await asyncio.sleep(0.05)
        peak = max(peak, len(env.runtime.queue.running()))
    assert peak == cap
    assert env.runtime.stats()["queue_depth"] == 4
    env.scenario.hang = False
    await env.runtime.stop()
