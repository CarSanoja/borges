from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest

from borges.api.app import create_app
from borges.cases.registry import CaseRegistry
from borges.runtime.jobs import DEAD, NewJob
from tests.identity.keys import bearer, make_key
from tests.runs.engine_fakes import Scenario, install
from tests.runs.fakes import make_rig
from tests.runtime.fake_runtime import transient_error
from tests.runtime.rig import wait_for

pytestmark = pytest.mark.timeout(60)


class Env:
    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **settings) -> None:
        self.scenario = Scenario()
        install(monkeypatch, self.scenario)
        self.rig = make_rig(tmp_path)
        resolved = self.rig.orchestrator.settings.model_copy(
            update={
                "borges_runtime_poll_s": 0.05,
                "borges_job_backoff_s": 0.01,
                "borges_job_max_attempts": 2,
                **settings,
            }
        )
        self.rig.orchestrator.settings = resolved
        self.app = create_app(
            settings=resolved,
            orchestrator=self.rig.orchestrator,
            registry=CaseRegistry(resolved.borges_cases_dir),
            store=self.rig.store,
            bus=self.rig.bus,
        )

    @property
    def runtime(self):
        return self.app.state.runtime

    @property
    def settings(self):
        return self.app.state.settings

    def client(self, host: str = "10.0.0.1") -> httpx.AsyncClient:
        transport = httpx.ASGITransport(app=self.app, client=(host, 5000))
        return httpx.AsyncClient(transport=transport, base_url="http://t")


@pytest.fixture
def env(tmp_path, monkeypatch) -> Env:
    return Env(tmp_path, monkeypatch)


BODY = {"case_id": "demo", "llm": "scripted"}


async def finish(env: Env) -> None:
    await env.runtime.drain(30)


async def test_an_anonymous_run_goes_through_the_queue(env: Env) -> None:
    async with env.client() as client:
        created = await client.post("/api/runs", json=BODY)
        run_id = created.json()["run_id"]
        await finish(env)
        snapshot = (await client.get(f"/api/runs/{run_id}")).json()
    assert created.status_code == 202 and snapshot["status"] == "completed"
    assert env.runtime.queue.get(run_id).source == "api"
    await env.runtime.stop()


async def test_idempotency_key_returns_the_same_run(env: Env) -> None:
    headers = {"Idempotency-Key": "click-1"}
    async with env.client() as client:
        first = await client.post("/api/runs", json=BODY, headers=headers)
        second = await client.post("/api/runs", json=BODY, headers=headers)
        await finish(env)
    assert first.json() == second.json()
    assert second.headers["Idempotent-Replay"] == "true"
    assert "Idempotent-Replay" not in first.headers
    assert len(env.rig.store.list_runs()) == 1
    await env.runtime.stop()


async def test_identical_requests_within_the_window_are_one_run(env: Env) -> None:
    async with env.client() as client:
        first = await client.post("/api/runs", json=BODY)
        second = await client.post("/api/runs", json=BODY)
        other = await client.post("/api/runs", json={**BODY, "max_universes": 3})
        await finish(env)
    assert first.json() == second.json() and second.headers["Idempotent-Replay"] == "true"
    assert other.json() != first.json()
    await env.runtime.stop()


async def test_a_different_client_gets_its_own_run(env: Env) -> None:
    async with env.client("10.0.0.1") as one, env.client("10.0.0.2") as two:
        a = await one.post("/api/runs", json=BODY)
        b = await two.post("/api/runs", json=BODY)
        await finish(env)
    assert a.json() != b.json()
    await env.runtime.stop()


async def test_malformed_idempotency_key_is_rejected(env: Env) -> None:
    async with env.client() as client:
        response = await client.post("/api/runs", json=BODY, headers={"Idempotency-Key": "a b"})
    assert response.status_code == 400 and "Idempotency-Key" in response.json()["detail"]


async def test_replay_does_not_spend_the_quota(env: Env) -> None:
    async with env.client() as client:
        for _ in range(12):
            assert (await client.post("/api/runs", json=BODY)).status_code == 202
        await finish(env)
    assert len(env.rig.store.list_runs()) == 1
    await env.runtime.stop()


async def test_creator_can_cancel_a_running_run_and_a_stranger_cannot(env: Env) -> None:
    env.scenario.hang = True
    async with env.client("10.0.0.1") as owner, env.client("10.0.0.9") as stranger:
        run_id = (await owner.post("/api/runs", json=BODY)).json()["run_id"]
        await wait_for(lambda: env.scenario.entered_plan.is_set())
        refused = await stranger.post(f"/api/runs/{run_id}/cancel")
        assert refused.status_code == 403
        env.scenario.hang = False
        accepted = await owner.post(f"/api/runs/{run_id}/cancel")
        assert accepted.status_code == 202 and accepted.json() == {
            "run_id": run_id,
            "status": "requested",
        }
    await env.runtime.stop()


async def test_cancelled_run_state_is_visible_and_cannot_be_cancelled_twice(env: Env) -> None:
    env.runtime.settings = env.runtime.settings.model_copy(update={"borges_max_active_runs": 1})
    env.runtime._admit = __import__("borges.runtime.admission", fromlist=["make_admit"]).make_admit(
        env.runtime.settings
    )
    env.scenario.hang = True
    async with env.client("10.0.0.1") as one, env.client("10.0.0.2") as two:
        await one.post("/api/runs", json=BODY)
        queued = (await two.post("/api/runs", json=BODY)).json()["run_id"]
        waiting = (await two.get(f"/api/runs/{queued}")).json()
        assert waiting["status"] == "queued"
        assert (await two.post(f"/api/runs/{queued}/cancel")).json()["status"] == "cancelled"
        assert (await two.get(f"/api/runs/{queued}")).json()["status"] == "cancelled"
        again = await two.post(f"/api/runs/{queued}/cancel")
        assert again.status_code == 409
    await env.runtime.stop()


async def test_cancel_of_an_unknown_run_is_404(env: Env) -> None:
    async with env.client() as client:
        assert (await client.post("/api/runs/r_nope/cancel")).status_code == 404


async def test_a_named_key_cancels_only_its_own_runs_and_admin_cancels_any(env: Env) -> None:
    env.scenario.hang = True
    alice = bearer(make_key(env.settings, "runs:create:scripted,runs:read", "alice"))
    bob = bearer(make_key(env.settings, "runs:create:scripted,runs:read", "bob"))
    root = bearer(make_key(env.settings, "admin", "root"))
    async with env.client() as client:
        run_id = (await client.post("/api/runs", json=BODY, headers=alice)).json()["run_id"]
        await wait_for(lambda: env.scenario.entered_plan.is_set())
        assert (await client.post(f"/api/runs/{run_id}/cancel", headers=bob)).status_code == 403
        env.scenario.hang = False
        assert (await client.post(f"/api/runs/{run_id}/cancel", headers=root)).status_code == 202
    await env.runtime.stop()


async def test_dead_letter_listing_is_admin_only(env: Env) -> None:
    env.scenario.plan_error = transient_error()
    async with env.client() as client:
        run_id = (await client.post("/api/runs", json=BODY)).json()["run_id"]
        await wait_for(lambda: env.runtime.queue.get(run_id).state == DEAD)
        anonymous = await client.get("/api/runs/dead-letter")
        admin = bearer(make_key(env.settings, "admin", "root"))
        listing = await client.get("/api/runs/dead-letter", headers=admin)
    assert anonymous.status_code == 403
    [entry] = listing.json()
    assert entry["run_id"] == run_id and entry["attempts"] == 2
    assert "ConnectError" in entry["error"] and entry["last_checkpoint"] is None
    await env.runtime.stop()


async def test_schedules_listing_is_admin_only(env: Env) -> None:
    env.runtime.schedules.add("demo", 3600.0, "operator", "scripted")
    async with env.client() as client:
        assert (await client.get("/api/schedules")).status_code == 403
        admin = bearer(make_key(env.settings, "admin", "root"))
        rows = (await client.get("/api/schedules", headers=admin)).json()
    assert [r["case_id"] for r in rows] == ["demo"] and rows[0]["every_s"] == 3600.0


async def test_health_reports_capacity(env: Env) -> None:
    env.runtime.settings = env.runtime.settings.model_copy(update={"borges_max_active_runs": 1})
    env.scenario.hang = True
    async with env.client("10.0.0.1") as one, env.client("10.0.0.2") as two:
        idle = (await one.get("/api/health")).json()
        assert idle["queue_depth"] == 0 and idle["active_workers"] == 0
        assert idle["oldest_job_age_s"] is None and idle["dead_letter_count"] == 0
        await one.post("/api/runs", json=BODY)
        await wait_for(lambda: env.scenario.entered_plan.is_set())
        await asyncio.sleep(0.05)
        busy = (await two.get("/api/health")).json()
    assert busy["active_workers"] == 1
    await env.runtime.stop()


async def test_lifespan_keeps_a_queued_run_the_old_reconcile_would_have_failed(
    tmp_path, monkeypatch
) -> None:
    env = Env(tmp_path, monkeypatch)
    env.rig.store.create(
        "r_orphan",
        {
            "case_id": "demo",
            "title": "t",
            "status": "running",
            "created_at": 1.0,
            "llm": "scripted",
            "backend": "local",
            "cost_usd": 0.0,
            "n_universes": 0,
            "verdict": None,
            "flipped_verdict": None,
            "owner_pid": 999999,
            "owner_host": __import__("socket").gethostname(),
        },
    )
    env.runtime.queue.submit(
        NewJob(
            run_id="r_orphan",
            principal="caller://anonymous",
            owner_key="caller://anonymous|1",
            anonymous=True,
            live=False,
            request='{"case_id": "demo", "llm": "scripted"}',
            max_attempts=3,
        )
    )
    async with env.app.router.lifespan_context(env.app):
        assert env.runtime._started is True
        await env.runtime.drain(30)
    assert env.rig.store.snapshot("r_orphan").status == "completed"
    assert env.runtime._started is False
