from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.api.platform_catalog import ORDER, PILLARS
from borges.api.platform_guard import SCORE_FILE
from borges.config import REPO_ROOT
from tests.api.test_routes_runs import Env
from tests.api.test_routes_runtime import Env as RuntimeEnv
from tests.armor.corpus_runner import evaluate, load
from tests.identity.keys import bearer, make_key

KEY = "p" * 32


@pytest.fixture
def env(tmp_path: Path) -> Env:
    return Env(tmp_path, key=None, borges_memory=True, borges_memory_key=KEY)


async def test_anonymous_sees_all_seven_pillars_without_secrets(env: Env) -> None:
    async with env.client() as client:
        response = await client.get("/api/platform")
    body = response.json()
    assert response.status_code == 200
    assert [p["id"] for p in body["pillars"]] == list(ORDER)
    assert {p["status"] for p in body["pillars"]} <= {"ok", "attention", "off", "error"}
    text = response.text.lower()
    for word in (KEY, "secret_hash", "bearer ", "nebius_api"):
        assert word not in text
    for pillar in body["pillars"]:
        assert pillar["verify"] and pillar["code"] and pillar["tests"] and pillar["summary"]


async def test_pillar_facts_come_from_the_running_system(env: Env) -> None:
    async with env.client() as client:
        pillars = {p["id"]: p for p in (await client.get("/api/platform")).json()["pillars"]}
    registry = pillars["registry"]["facts"]
    assert registry["agents"] > 0 and len(registry["registry_sha"]) == 64
    assert pillars["runtime"]["status"] == "off"
    memory = pillars["memory"]["facts"]
    assert memory["enabled"] and memory["encrypted"] and "tenants" not in memory
    identity = pillars["identity"]["facts"]
    assert identity["kind"] == "anonymous" and identity["scopes"] == identity["anonymous_scopes"]
    gateway = pillars["gateway"]["facts"]
    assert len(gateway["policy_sha"]) == 64 and gateway["agents"]["judge"]["models"]
    armor = pillars["armor"]["facts"]
    assert armor["corpus"]["detection_rate"] == 1.0 and "email" in armor["pii_kinds"]
    observability = pillars["observability"]["facts"]
    assert observability["exporter"] == "local"
    assert observability["audit_chain"]["ok"] is True


async def test_keyed_callers_also_see_the_tenant_count(env: Env) -> None:
    headers = bearer(make_key(env.app.state.settings, "memory:read", "alice"))
    async with env.client() as client:
        pillars = (await client.get("/api/platform", headers=headers)).json()["pillars"]
    by_id = {p["id"]: p for p in pillars}
    assert by_id["memory"]["facts"]["tenants"] == 0
    assert by_id["identity"]["facts"]["kind"] == "key"
    assert by_id["identity"]["facts"]["keystore"]["ok"] is True


async def test_a_broken_global_audit_chain_is_reported(env: Env) -> None:
    from borges.telemetry.run_telemetry import global_audit_path

    path = global_audit_path(env.app.state.settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"seq": 1, "bogus": true}\n', encoding="utf-8")
    async with env.client() as client:
        pillars = (await client.get("/api/platform")).json()["pillars"]
    chain = next(p for p in pillars if p["id"] == "observability")
    assert chain["status"] == "error" and chain["facts"]["audit_chain"]["ok"] is False


def test_every_listed_code_and_test_path_exists() -> None:
    for key, pillar in PILLARS.items():
        for relative in (*pillar["code"], *pillar["tests"]):
            assert (REPO_ROOT / relative).exists(), f"{key}: {relative}"


def test_the_published_armor_score_matches_the_corpus() -> None:
    suites = json.loads(SCORE_FILE.read_text(encoding="utf-8"))["suites"]
    measured = []
    for name, attacks, benign in (
        ("attacks", "attacks.json", "benign.json"),
        ("redteam", "attacks_redteam.json", "benign_redteam.json"),
    ):
        score = evaluate(attacks, benign)
        measured.append(
            {
                "name": name,
                "attacks": len(load(attacks)),
                "detected": score.true_positives,
                "benign": score.benign_total,
                "false_positives": len(score.false_positives),
            }
        )
    assert suites == measured


async def test_an_attached_runtime_reports_queue_and_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = RuntimeEnv(tmp_path, monkeypatch)
    async with env.client() as client:
        pillars = (await client.get("/api/platform")).json()["pillars"]
    runtime = next(p for p in pillars if p["id"] == "runtime")
    assert runtime["status"] == "ok"
    assert runtime["facts"]["queue_depth"] == 0 and runtime["facts"]["dead_letter_count"] == 0
    assert runtime["facts"]["resume_from_checkpoints"] is True
    assert runtime["facts"]["max_attempts"] == 2
