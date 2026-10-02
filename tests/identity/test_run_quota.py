from __future__ import annotations

import pytest
from fastapi import HTTPException

from borges.config import Settings
from borges.identity.principal import ANONYMOUS, Principal
from borges.identity.run_quota import RunQuota
from tests.api.test_routes_runs import Env
from tests.identity.keys import bearer, make_key


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


NAMED = Principal(id="caller://ci", kind="key", scopes=frozenset())


def test_an_anonymous_client_holds_one_run_slot_at_a_time() -> None:
    quota, active = RunQuota(settings()), set()
    quota.admit(ANONYMOUS, "1.1.1.1", False, active.__contains__)
    quota.record(ANONYMOUS, "1.1.1.1", "r1")
    active.add("r1")
    with pytest.raises(HTTPException) as busy:
        quota.admit(ANONYMOUS, "1.1.1.1", False, active.__contains__)
    assert busy.value.status_code == 429 and "Retry-After" in busy.value.headers
    quota.admit(ANONYMOUS, "2.2.2.2", False, active.__contains__)
    active.clear()
    quota.admit(ANONYMOUS, "1.1.1.1", False, active.__contains__)


def test_scripted_and_live_starts_are_rate_limited_separately() -> None:
    clock = Clock()
    quota = RunQuota(settings(borges_anon_live_runs_per_hour=2.0), clock)
    for _ in range(6):
        quota.admit(ANONYMOUS, "1.1.1.1", False, lambda _: False)
    with pytest.raises(HTTPException, match="scripted"):
        quota.admit(ANONYMOUS, "1.1.1.1", False, lambda _: False)
    quota.admit(ANONYMOUS, "1.1.1.1", True, lambda _: False)
    quota.admit(ANONYMOUS, "1.1.1.1", True, lambda _: False)
    with pytest.raises(HTTPException, match="live"):
        quota.admit(ANONYMOUS, "1.1.1.1", True, lambda _: False)
    clock.now += 3600
    quota.admit(ANONYMOUS, "1.1.1.1", True, lambda _: False)


def test_named_principals_get_more_room_and_are_not_keyed_by_address() -> None:
    quota, active = RunQuota(settings()), {f"r{i}" for i in range(3)}
    for run in sorted(active):
        quota.admit(NAMED, "1.1.1.1", False, active.__contains__)
        quota.record(NAMED, "9.9.9.9", run)
    quota.admit(NAMED, "5.5.5.5", False, active.__contains__)
    quota.record(NAMED, "5.5.5.5", "r3")
    active.add("r3")
    with pytest.raises(HTTPException):
        quota.admit(NAMED, "6.6.6.6", False, active.__contains__)


def test_owner_table_stays_bounded(monkeypatch) -> None:
    monkeypatch.setattr("borges.identity.run_quota.MAX_OWNERS", 20)
    quota = RunQuota(settings())
    for index in range(100):
        quota.admit(ANONYMOUS, f"10.0.0.{index}", False, lambda _: False)
    assert len(quota._owners) <= 21


async def test_the_route_refuses_a_second_concurrent_anonymous_run(tmp_path) -> None:
    env = Env(tmp_path, key="k")
    env.orchestrator.tasks = {"new-run": object()}
    async with env.client() as client:
        first = await client.post("/api/runs", json={"case_id": "a"})
        second = await client.post("/api/runs", json={"case_id": "a"})
        keyed = await client.post(
            "/api/runs",
            json={"case_id": "a"},
            headers=bearer(make_key(env.app.state.settings, "admin")),
        )
    assert first.status_code == 202
    assert second.status_code == 429 and second.headers["retry-after"]
    assert keyed.status_code == 202
