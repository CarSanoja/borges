from __future__ import annotations

import pytest

from borges.identity.principal import ANONYMOUS, Principal
from borges.identity.run_access import can_read_run, meta_is_public, run_is_public
from borges.identity.scopes import ADMIN, PUBLIC_SCOPES
from tests.api.test_routes_runtime import BODY, Env
from tests.identity.keys import bearer, make_key

pytestmark = pytest.mark.timeout(90)

SCOPES = "runs:create:scripted,runs:read"


@pytest.fixture
def env(tmp_path, monkeypatch) -> Env:
    return Env(tmp_path, monkeypatch)


def named(id_: str) -> Principal:
    return Principal(id=f"caller://{id_}", kind="key", scopes=PUBLIC_SCOPES)


def paths(run_id: str) -> list[str]:
    return [
        f"/api/runs/{run_id}",
        f"/api/runs/{run_id}/events?from_seq=0",
        f"/api/runs/{run_id}/trace",
        f"/api/runs/{run_id}/audit",
        f"/api/runs/{run_id}/universes/u_x",
        f"/api/runs/{run_id}/universes/u_x/script",
    ]


async def test_principal_b_gets_404_on_principal_a_private_run(env: Env) -> None:
    alice = bearer(make_key(env.settings, SCOPES, "alice"))
    bob = bearer(make_key(env.settings, SCOPES, "bob"))
    async with env.client() as client:
        run_id = (await client.post("/api/runs", json=BODY, headers=alice)).json()["run_id"]
        await env.runtime.drain(30)
        for url in paths(run_id):
            assert (await client.get(url, headers=bob)).status_code == 404, url
            assert (await client.get(url)).status_code == 404, url
        assert (await client.get(f"/api/runs/{run_id}", headers=alice)).status_code == 200
        assert (await client.get(f"/api/runs/{run_id}/audit", headers=alice)).status_code == 200
        mine = (await client.get("/api/runs", headers=alice)).json()
        theirs = (await client.get("/api/runs", headers=bob)).json()
        assert [r["run_id"] for r in mine] == [run_id]
        assert theirs == []
    await env.runtime.stop()


async def test_admin_reads_any_run_and_creator_can_share_it(env: Env) -> None:
    alice = bearer(make_key(env.settings, SCOPES, "alice"))
    bob = bearer(make_key(env.settings, SCOPES, "bob"))
    admin = bearer(make_key(env.settings, ADMIN, "root"))
    async with env.client() as client:
        run_id = (await client.post("/api/runs", json=BODY, headers=alice)).json()["run_id"]
        await env.runtime.drain(30)
        assert (await client.get(f"/api/runs/{run_id}", headers=admin)).status_code == 200
        assert (await client.post(f"/api/runs/{run_id}/share", headers=bob)).status_code == 404
        assert (await client.post(f"/api/runs/{run_id}/share")).status_code == 404
        shared = await client.post(f"/api/runs/{run_id}/share", headers=alice)
        assert shared.json() == {"run_id": run_id, "public": True}
        assert (await client.get(f"/api/runs/{run_id}", headers=bob)).status_code == 200
        assert (await client.get(f"/api/runs/{run_id}")).status_code == 200
    await env.runtime.stop()


async def test_anonymous_demo_run_on_a_curated_case_stays_public(env: Env) -> None:
    async with env.client("10.0.0.1") as one, env.client("10.0.0.2") as two:
        run_id = (await one.post("/api/runs", json=BODY)).json()["run_id"]
        await env.runtime.drain(30)
        assert env.rig.store.meta(run_id)["public"] is True
        assert (await two.get(f"/api/runs/{run_id}")).status_code == 200
        assert (await two.get(f"/api/runs/{run_id}/audit")).status_code == 200
        listed = (await two.get("/api/runs")).json()
        assert run_id in [r["run_id"] for r in listed]
    await env.runtime.stop()


def test_visibility_rules() -> None:
    alice, bob = named("alice"), named("bob")
    admin = Principal(id="caller://root", kind="key", scopes=frozenset({ADMIN}))
    private = {"case_id": "demo", "principal": alice.id, "public": False}
    assert can_read_run(private, alice) and can_read_run(private, admin)
    assert not can_read_run(private, bob) and not can_read_run(private, ANONYMOUS)
    assert can_read_run({**private, "public": True}, bob)


def test_public_means_curated_case_by_an_anonymous_caller() -> None:
    assert run_is_public("demo", False, ANONYMOUS)
    assert not run_is_public(None, True, ANONYMOUS)
    assert not run_is_public("demo", False, named("alice"))
    assert not run_is_public("demo", True, ANONYMOUS)


def test_legacy_metas_without_an_owner_are_public_only_for_curated_cases() -> None:
    assert meta_is_public({"case_id": "checkout_ab"})
    assert not meta_is_public({"case_id": None})
    assert not meta_is_public({"case_id": "demo", "principal": "caller://alice"})
