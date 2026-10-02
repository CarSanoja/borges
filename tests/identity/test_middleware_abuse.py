from __future__ import annotations

import pytest

from borges.telemetry.audit_verify import read_records
from borges.telemetry.run_telemetry import global_audit_path
from tests.api.test_routes_runs import Env
from tests.identity.keys import bearer, make_key


def denials(env: Env):
    path = global_audit_path(env.app.state.settings)
    if not path.exists():
        return []
    return [r for r in read_records(path) if r.decision == "deny"]


@pytest.fixture
def env(tmp_path) -> Env:
    return Env(tmp_path, key="k", borges_rate_anon_burst=20, borges_rate_anon_per_s=0.01)


async def test_a_flood_of_bad_keys_is_rate_limited_and_audited_once(env: Env) -> None:
    async with env.client() as client:
        codes = [
            (await client.get("/api/cases", headers=bearer(f"bk_aaaa_{i}"))).status_code
            for i in range(60)
        ]
    assert codes[:20] == [401] * 20
    assert set(codes[20:]) == {429}
    assert len(denials(env)) <= 3


async def test_repeated_forbidden_calls_do_not_each_write_an_audit_record(env: Env) -> None:
    async with env.client() as client:
        codes = [(await client.get("/api/audit")).status_code for _ in range(15)]
    assert set(codes) == {403}
    assert len(denials(env)) == 1


async def test_a_bad_key_flood_does_not_block_other_clients_or_named_keys(env: Env) -> None:
    token = make_key(env.app.state.settings, "audit:read")
    async with env.client() as client:
        for i in range(40):
            await client.get("/api/cases", headers=bearer(f"bk_aaaa_{i}"))
        assert (await client.get("/api/audit", headers=bearer(token))).status_code == 200


async def test_two_authorization_headers_are_rejected(env: Env) -> None:
    token = make_key(env.app.state.settings, "audit:read")
    async with env.client() as client:
        response = await client.get(
            "/api/audit",
            headers=[("Authorization", f"Bearer {token}"), ("Authorization", f"Bearer {token}")],
        )
    assert response.status_code == 401
