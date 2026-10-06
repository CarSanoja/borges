from __future__ import annotations

import pytest

from borges.identity.keystore import open_keystore
from borges.telemetry.audit_verify import read_records
from borges.telemetry.run_telemetry import global_audit_path
from tests.api.test_routes_runs import Env
from tests.identity.keys import bearer, make_key

PUBLIC_GETS = ["/api/health", "/api/cases", "/api/runs", "/api/me", "/api/agents"]


def audit_of(env: Env, kind: str = "identity.access"):
    path = global_audit_path(env.app.state.settings)
    return [r for r in read_records(path) if r.kind == kind]


@pytest.fixture
def env(tmp_path) -> Env:
    return Env(tmp_path, key="k")


async def test_anonymous_can_do_the_public_demo_path(env: Env) -> None:
    async with env.client() as client:
        for path in PUBLIC_GETS:
            assert (await client.get(path)).status_code == 200, path
        assert (await client.get("/api/runs/r1")).status_code == 200
        scripted = await client.post("/api/runs", json={"case_id": "a", "llm": "scripted"})
        live = await client.post("/api/runs", json={"case_id": "a", "llm": "nebius"})
    assert scripted.status_code == 202
    assert live.status_code == 202


async def test_anonymous_can_do_nothing_else(env: Env) -> None:
    upload = {"file": ("d.csv", b"a,b\n1,2\n", "text/csv")}
    async with env.client() as client:
        denied = [
            await client.post("/api/uploads", files=upload),
            await client.post("/api/agents/publish"),
            await client.post("/api/agents/judge/versions/1.0.0/approve"),
            await client.get("/api/audit"),
            await client.post(
                "/api/runs",
                json={
                    "upload_id": "u" * 32,
                    "llm": "nebius",
                    "question": "q",
                    "decision_rule": {"metric": "effect"},
                },
            ),
        ]
    assert [r.status_code for r in denied] == [403] * 5
    assert "Anonymous demo access" in denied[0].json()["detail"]
    assert "uploads:write" in denied[0].json()["detail"]


async def test_denials_are_audited_with_the_principal(env: Env) -> None:
    async with env.client() as client:
        await client.get("/api/audit")
    deny = [r for r in audit_of(env) if r.decision == "deny"]
    assert deny and deny[-1].principal == "caller://anonymous"
    assert deny[-1].data["scope"] == "audit:read"


async def test_named_key_with_scope_works(env: Env) -> None:
    token = make_key(env.app.state.settings, "audit:read", name="auditor")
    async with env.client() as client:
        response = await client.get("/api/audit", headers=bearer(token))
        me = await client.get("/api/me", headers=bearer(token))
    assert response.status_code == 200
    assert me.json()["principal"] == "caller://auditor"
    allows = [r for r in audit_of(env) if r.decision == "allow"]
    assert any(
        r.principal == "caller://auditor" and r.data["route"] == "/api/audit" for r in allows
    )


async def test_named_key_without_the_scope_is_still_denied(env: Env) -> None:
    token = make_key(env.app.state.settings, "uploads:write", name="uploader")
    async with env.client() as client:
        assert (await client.get("/api/audit", headers=bearer(token))).status_code == 403


async def test_revoked_and_expired_keys_fail_with_401(env: Env) -> None:
    settings = env.app.state.settings
    store = open_keystore(settings)
    record, revoked = store.create("old", "audit:read")
    store.revoke(record.key_id)
    _, expired = store.create("late", "audit:read", ttl_s=1, now=1.0)
    async with env.client() as client:
        for token in (revoked, expired, "bk_nope_nope", "not-a-key"):
            response = await client.get("/api/audit", headers=bearer(token))
            assert response.status_code == 401, token
        assert (await client.get("/api/cases", headers=bearer(revoked))).status_code == 401
    assert any("revoked" in (r.reason or "") for r in audit_of(env))


async def test_undeclared_route_is_denied_and_audited(env: Env) -> None:
    @env.app.get("/api/secret")
    def secret() -> dict[str, str]:
        return {"leak": "yes"}

    async with env.client() as client:
        response = await client.get("/api/secret")
        named = await client.get(
            "/api/secret", headers=bearer(make_key(env.app.state.settings, "admin"))
        )
    assert response.status_code == 403
    assert named.status_code == 403
    deny = audit_of(env)[-1]
    assert deny.decision == "deny" and "failing closed" in deny.reason


async def test_rate_limit_returns_429_with_retry_after(tmp_path) -> None:
    env = Env(tmp_path, key=None, borges_rate_anon_burst=3, borges_rate_anon_per_s=0.01)
    async with env.client() as client:
        codes = [(await client.get("/api/cases")).status_code for _ in range(5)]
        limited = await client.get("/api/cases")
    assert codes[:3] == [200] * 3 and codes[3:] == [429, 429]
    assert int(limited.headers["retry-after"]) >= 1
    assert any(r.reason == "rate limit exceeded" for r in audit_of(env))


async def test_rate_limit_is_per_principal(tmp_path) -> None:
    env = Env(tmp_path, key=None, borges_rate_anon_burst=1, borges_rate_anon_per_s=0.01)
    token = make_key(env.app.state.settings, "audit:read")
    async with env.client() as client:
        await client.get("/api/cases")
        assert (await client.get("/api/cases")).status_code == 429
        assert (await client.get("/api/cases", headers=bearer(token))).status_code == 200


async def test_legacy_live_token_maps_to_upload_scopes(tmp_path) -> None:
    env = Env(tmp_path, key="k", borges_live_token="s3cret")
    headers = {"X-Borges-Live-Token": "s3cret"}
    async with env.client() as client:
        me = await client.get("/api/me", headers=headers)
        audit = await client.get("/api/audit", headers=headers)
    assert me.json()["principal"] == "caller://legacy-live-token"
    assert "uploads:write" in me.json()["scopes"]
    assert audit.status_code == 403


async def test_public_reads_are_not_audited_unless_asked(tmp_path) -> None:
    quiet = Env(tmp_path / "q", key=None)
    loud = Env(tmp_path / "l", key=None, borges_audit_reads=True)
    for env in (quiet, loud):
        async with env.client() as client:
            await client.get("/api/cases")
    assert not any(r.data["route"] == "/api/cases" for r in audit_of(quiet))
    assert any(r.data["route"] == "/api/cases" for r in audit_of(loud))


async def test_non_api_paths_are_not_gated(tmp_path) -> None:
    env = Env(tmp_path, key=None)
    async with env.client() as client:
        assert (await client.get("/")).status_code in (200, 404)


async def test_unknown_api_paths_are_a_plain_404(env: Env) -> None:
    async with env.client() as client:
        assert (await client.get("/api/nothing")).status_code == 404


UNKNOWN_PATHS = [
    "/api/nothing",
    "/api/cases/checkout_ab/nothing",
    "/api/runs/r1/nothing/deeper",
    "/api/health/extra",
    "/api",
    "/api/",
]
METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


@pytest.mark.parametrize("path", UNKNOWN_PATHS)
async def test_every_method_on_an_unknown_api_path_is_the_same_404(env: Env, path: str) -> None:
    async with env.client() as client:
        responses = [await client.request(method, path) for method in METHODS]
        keyed = await client.get(path, headers=bearer("bk_aaaa_bad"))
    assert [r.status_code for r in responses] == [404] * len(METHODS)
    assert keyed.status_code == 404
    bodies = {r.json()["detail"] for r in responses if r.request.method != "HEAD"}
    assert bodies == {"Not found."}


async def test_known_routes_keep_their_status_codes(env: Env) -> None:
    async with env.client() as client:
        assert (await client.get("/api/health")).status_code == 200
        assert (await client.get("/api/audit")).status_code == 403


async def test_a_broken_key_store_gives_503_for_keys_and_leaves_anonymous_routes_alone(
    env: Env,
) -> None:
    settings = env.app.state.settings
    store = open_keystore(settings)
    record, token = store.create("alice", "audit:read")
    store.create("bob", "audit:read")
    store.revoke(record.key_id)
    lines = store.path.read_text().splitlines()
    store.path.write_text("\n".join(lines[:-1]) + "\n")
    async with env.client() as client:
        keyed = await client.get("/api/audit", headers=bearer(token))
        keyed_public = await client.get("/api/cases", headers=bearer(token))
        anonymous = [await client.get(path) for path in PUBLIC_GETS]
        scripted = await client.post("/api/runs", json={"case_id": "a", "llm": "scripted"})
    assert keyed.status_code == 503 and keyed_public.status_code == 503
    assert "key store" in keyed.json()["detail"]
    assert [r.status_code for r in anonymous] == [200] * len(PUBLIC_GETS)
    assert scripted.status_code == 202
