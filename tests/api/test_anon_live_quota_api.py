from __future__ import annotations

from pathlib import Path

import pytest

from tests.api.test_routes_runs import Env
from tests.identity.keys import bearer, make_key

LIVE = {"case_id": "a", "llm": "nebius"}


def env_for(tmp_path: Path, **fields) -> Env:
    return Env(
        tmp_path, key="k", borges_anon_live_per_client_per_day=2, borges_max_live_runs=9, **fields
    )


def stored_bytes(root: Path) -> bytes:
    return b"".join(p.read_bytes() for p in root.rglob("*") if p.is_file())


async def post(client, headers: dict[str, str] | None = None):
    return await client.post("/api/runs", json=LIVE, headers=headers)


async def test_the_third_anonymous_live_run_is_429_with_the_reset_time(tmp_path: Path) -> None:
    env = env_for(tmp_path)
    async with env.client() as client:
        first = await post(client)
        second = await post(client)
        third = await post(client)
    assert first.status_code == second.status_code == 202
    assert first.json()["est_cost_usd"] == env.app.state.settings.borges_typical_run_cost_usd
    assert first.json()["live_quota"]["remaining"] == 1
    assert second.json()["live_quota"]["remaining"] == 0
    assert third.status_code == 429
    assert "resets at" in third.json()["detail"] and "Retry-After" in third.headers
    assert len(env.orchestrator.calls) == 2


async def test_scripted_runs_do_not_spend_the_live_quota(tmp_path: Path) -> None:
    env = env_for(tmp_path)
    async with env.client() as client:
        for _ in range(3):
            response = await client.post("/api/runs", json={"case_id": "a"})
            assert response.status_code == 202
            assert response.json() == {"run_id": "new-run"}
        assert (await post(client)).status_code == 202


async def test_keyed_principals_bypass_the_anonymous_quota(tmp_path: Path) -> None:
    env = env_for(tmp_path)
    headers = bearer(make_key(env.app.state.settings, "runs:create:live:curated", "alice"))
    async with env.client() as client:
        for _ in range(4):
            response = await post(client, headers)
            assert response.status_code == 202
            assert "live_quota" not in response.json()
        assert (await post(client)).status_code == 202


async def test_the_global_hourly_cap_blocks_every_anonymous_client(tmp_path: Path) -> None:
    env = env_for(
        tmp_path,
        borges_anon_live_global_per_hour=1,
        borges_trusted_proxy=True,
    )
    async with env.client() as client:
        assert (await post(client, {"X-Forwarded-For": "9.9.9.1"})).status_code == 202
        refused = await post(client, {"X-Forwarded-For": "9.9.9.2"})
    assert refused.status_code == 429 and "per hour on this server" in refused.json()["detail"]


@pytest.mark.parametrize("trusted", [False, True])
async def test_forwarded_for_counts_only_behind_a_trusted_proxy(
    tmp_path: Path, trusted: bool
) -> None:
    env = env_for(tmp_path, borges_trusted_proxy=trusted)
    async with env.client() as client:
        codes = [
            (await post(client, {"X-Forwarded-For": f"9.9.9.{index}"})).status_code
            for index in range(3)
        ]
    assert codes == ([202, 202, 202] if trusted else [202, 202, 429])


async def test_health_states_cost_and_remaining_quota(tmp_path: Path) -> None:
    env = env_for(tmp_path)
    async with env.client() as client:
        await post(client)
        body = (await client.get("/api/health")).json()
    quota = body["anon_live_quota"]
    assert quota["applies"] is True and quota["remaining"] == 1
    assert quota["per_client_per_day"] == 2 and quota["resets_at"]
    assert body["est_cost_per_live_run_usd"] == env.app.state.settings.borges_typical_run_cost_usd
    assert body["max_cost_per_live_run_usd"] == env.app.state.settings.borges_run_cap_usd
    assert "203.0.113" not in str(body)


async def test_the_database_holds_a_hash_not_the_address(tmp_path: Path) -> None:
    env = env_for(tmp_path, borges_trusted_proxy=True)
    async with env.client() as client:
        await post(client, {"X-Forwarded-For": "203.0.113.5"})
    assert b"203.0.113.5" not in stored_bytes(tmp_path)
