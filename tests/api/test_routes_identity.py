from __future__ import annotations

from borges.telemetry.audit_log import AuditLog
from borges.telemetry.run_telemetry import global_audit_path
from tests.api.test_routes_runs import Env
from tests.identity.keys import bearer, make_key


async def test_me_describes_the_anonymous_demo_principal(tmp_path) -> None:
    env = Env(tmp_path, key=None)
    async with env.client() as client:
        body = (await client.get("/api/me")).json()
    assert body["principal"] == "caller://anonymous"
    assert body["anonymous"] is True
    assert set(body["scopes"]) == {
        "cases:read",
        "memory:read",
        "recordings:read",
        "runs:create:live:curated",
        "runs:create:scripted",
        "runs:read",
    }
    assert body["rate_limit"]["limit"] == env.app.state.settings.borges_rate_anon_burst
    assert body["rate_limit"]["remaining"] < body["rate_limit"]["limit"]


async def test_me_for_a_named_key_shows_scopes_and_expiry(tmp_path) -> None:
    env = Env(tmp_path, key=None)
    token = make_key(env.app.state.settings, "audit:read", name="ops", ttl_s=3600)
    async with env.client() as client:
        body = (await client.get("/api/me", headers=bearer(token))).json()
    assert body["principal"] == "caller://ops"
    assert body["kind"] == "key" and body["expires_at"] is not None
    assert "audit:read" in body["scopes"]
    assert body["rate_limit"]["limit"] == env.app.state.settings.borges_rate_key_burst


async def test_global_audit_needs_the_scope_and_filters(tmp_path) -> None:
    env = Env(tmp_path, key=None)
    log = AuditLog(global_audit_path(env.app.state.settings))
    log.append("x.one", principal="caller://a", decision="allow")
    log.append("x.two", principal="caller://b", decision="deny")
    token = make_key(env.app.state.settings, "audit:read")
    async with env.client() as client:
        assert (await client.get("/api/audit")).status_code == 403
        everything = (await client.get("/api/audit", headers=bearer(token))).json()
        denied = (
            await client.get("/api/audit?decision=deny&principal=caller://b", headers=bearer(token))
        ).json()
        verified = (await client.get("/api/audit?verify=true", headers=bearer(token))).json()
    assert everything["total"] >= 2
    assert [r["kind"] for r in denied["records"]] == ["x.two"]
    assert verified["chain"]["ok"] is True
