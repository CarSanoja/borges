from __future__ import annotations

import pytest

from borges.runtime.jobs import DEAD
from borges.telemetry.run_telemetry import global_audit_path
from tests.api.test_routes_runtime import BODY, Env
from tests.identity.keys import bearer, make_key
from tests.runtime.fake_runtime import transient_error
from tests.runtime.rig import wait_for

pytestmark = pytest.mark.timeout(60)


@pytest.fixture
def env(tmp_path, monkeypatch) -> Env:
    return Env(tmp_path, monkeypatch)


async def test_a_forced_dead_letter_is_visible_to_the_admin_and_audited(env: Env) -> None:
    env.scenario.plan_error = transient_error()
    admin = bearer(make_key(env.settings, "admin", "root"))
    async with env.client() as client:
        run_id = (await client.post("/api/runs", json=BODY)).json()["run_id"]
        await wait_for(lambda: env.runtime.queue.get(run_id).state == DEAD)
        assert (await client.get("/api/runs/dead-letter")).status_code == 403
        [entry] = (await client.get("/api/runs/dead-letter", headers=admin)).json()
        pillars = (await client.get("/api/platform")).json()["pillars"]
        detail = (await client.get(f"/api/runs/{run_id}")).json()
    assert entry["run_id"] == run_id and entry["attempts"] == env.settings.borges_job_max_attempts
    assert "ConnectError" in entry["error"] and entry["requeued_at"] is None
    runtime = next(p for p in pillars if p["id"] == "runtime")
    assert runtime["status"] == "attention" and runtime["facts"]["dead_letter_count"] == 1
    assert detail["status"] in ("failed", "queued", "running")
    audit = global_audit_path(env.settings).read_text()
    assert "runtime.dead_letter" in audit and run_id in audit
    await env.runtime.stop()


async def test_a_requeued_dead_letter_leaves_the_admin_listing_empty_after_it_resumes(
    env: Env,
) -> None:
    env.scenario.plan_error = transient_error()
    admin = bearer(make_key(env.settings, "admin", "root"))
    async with env.client() as client:
        run_id = (await client.post("/api/runs", json=BODY)).json()["run_id"]
        await wait_for(lambda: env.runtime.queue.get(run_id).state == DEAD)
        env.scenario.plan_error = None
        assert env.runtime.dead.requeue(run_id) is not None
        env.runtime.store.update_meta(run_id, status="queued")
        env.runtime.wake()
        await env.runtime.drain(30)
        listing = (await client.get("/api/runs/dead-letter", headers=admin)).json()
    assert all(item["requeued_at"] is not None for item in listing)
    await env.runtime.stop()
