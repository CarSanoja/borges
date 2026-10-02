from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from borges.api.app import create_app
from borges.armor.errors import ArmorRefusal
from borges.armor.report import ArmorDecision
from borges.config import Settings
from borges.runs.events import Event
from borges.runs.models import RunSnapshot, RunSummary
from borges.telemetry.run_telemetry import global_audit_path
from tests.identity.keys import bearer, make_key


def summary(run_id: str, status: str = "running", llm: str = "nebius") -> RunSummary:
    return RunSummary(
        run_id=run_id,
        case_id=None,
        title="t",
        status=status,
        created_at=1.0,
        llm=llm,
        backend="local",
        cost_usd=0.0,
        n_universes=0,
        verdict=None,
        flipped_verdict=None,
    )


class FakeStore:
    def __init__(self) -> None:
        self.runs: list[RunSummary] = [summary("r1", "completed", "scripted")]

    def list_runs(self) -> list[RunSummary]:
        return self.runs

    def exists(self, run_id: str) -> bool:
        return any(r.run_id == run_id for r in self.runs)


class FakeRegistry:
    def list(self) -> list:
        return []

    def recording(self, case_id: str):
        return None


class FakeOrchestrator:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, bytes | None, str | None]] = []
        self.active = 0
        self.live = 0

    def active_count(self) -> int:
        return self.active

    def live_count(self) -> int:
        return self.live

    async def start(self, request, data=None, dataset_name=None) -> str:
        self.calls.append((request, data, dataset_name))
        return "new-run"

    def snapshot(self, run_id: str) -> RunSnapshot:
        return RunSnapshot(run_id=run_id, title="hello")

    def universe_detail(self, run_id: str, universe_id: str):
        raise KeyError(universe_id)


class FakeBus:
    async def subscribe(self, run_id: str, from_seq: int) -> AsyncIterator[Event]:
        for seq in range(from_seq, 3):
            kind = "run.finished" if seq == 2 else "stage"
            yield Event(seq=seq, ts=0, run_id=run_id, type=kind)


class Env:
    def __init__(self, tmp_path, key: str | None, **overrides: Any) -> None:
        self.store = FakeStore()
        self.orchestrator = FakeOrchestrator()
        self.app = create_app(
            settings=Settings(
                _env_file=None, borges_home=tmp_path, nebius_api_key=key, **overrides
            ),
            orchestrator=self.orchestrator,
            registry=FakeRegistry(),
            store=self.store,
            bus=FakeBus(),
        )

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://t")


def uploader(env: Env) -> dict[str, str]:
    return bearer(make_key(env.app.state.settings, "runs:create:live:upload"))


@pytest.fixture
def env(tmp_path) -> Env:
    return Env(tmp_path, key=None)


async def test_create_run_for_case(env: Env) -> None:
    async with env.client() as client:
        response = await client.post("/api/runs", json={"case_id": "a"})
    assert response.status_code == 202
    assert response.json() == {"run_id": "new-run"}
    assert env.orchestrator.calls[0][1:] == (None, None)


async def test_create_run_needs_case_or_upload(env: Env) -> None:
    async with env.client() as client:
        assert (await client.post("/api/runs", json={})).status_code == 400


async def test_nebius_without_key_is_400(env: Env) -> None:
    async with env.client() as client:
        response = await client.post("/api/runs", json={"case_id": "a", "llm": "nebius"})
    assert response.status_code == 400
    assert "NEBIUS_API_KEY" in response.json()["detail"]


async def test_live_run_limit_is_429(tmp_path) -> None:
    env = Env(tmp_path, key="k")
    env.orchestrator.live = 2
    async with env.client() as client:
        response = await client.post("/api/runs", json={"case_id": "a", "llm": "nebius"})
        env.orchestrator.live = 1
        ok = await client.post("/api/runs", json={"case_id": "a", "llm": "nebius"})
    assert response.status_code == 429
    assert ok.status_code == 202


async def test_live_count_comes_from_memory_not_meta(tmp_path) -> None:
    env = Env(tmp_path, key="k")
    env.store.runs = [summary("a"), summary("b"), summary("c")]
    async with env.client() as client:
        response = await client.post("/api/runs", json={"case_id": "a", "llm": "nebius"})
    assert response.status_code == 202


async def test_upload_run_requires_question_and_rule(tmp_path) -> None:
    env = Env(tmp_path, key="k", borges_allow_untrusted_local=True)
    body = {"upload_id": "x" * 32, "llm": "nebius"}
    async with env.client() as client:
        response = await client.post("/api/runs", json=body, headers=uploader(env))
    assert response.status_code == 400
    assert "decision_rule" in response.json()["detail"]


async def test_upload_run_passes_bytes(tmp_path) -> None:
    env = Env(tmp_path, key="k", borges_allow_untrusted_local=True)
    env.app.state.uploads.get = lambda upload_id: (b"PQ", "d.csv")
    body = {
        "upload_id": "u" * 32,
        "llm": "nebius",
        "question": "q?",
        "decision_rule": {"metric": "effect"},
    }
    async with env.client() as client:
        response = await client.post("/api/runs", json=body, headers=uploader(env))
    assert response.status_code == 202
    _, data, name = env.orchestrator.calls[0]
    assert (data, name) == (b"PQ", "d.csv")


async def test_unknown_upload_is_400(tmp_path) -> None:
    env = Env(tmp_path, key="k", borges_allow_untrusted_local=True)
    body = {
        "upload_id": "0" * 32,
        "llm": "nebius",
        "question": "q",
        "decision_rule": {"metric": "m"},
    }
    async with env.client() as client:
        response = await client.post("/api/runs", json=body, headers=uploader(env))
        assert response.status_code == 400


async def test_list_and_get_run(env: Env) -> None:
    async with env.client() as client:
        runs = (await client.get("/api/runs")).json()
        snap = (await client.get("/api/runs/r1")).json()
        missing = await client.get("/api/runs/nope")
    assert runs[0]["run_id"] == "r1"
    assert snap["title"] == "hello"
    assert missing.status_code == 404


async def test_armor_refusal_is_400_and_audited(env: Env) -> None:
    decision = ArmorDecision("refuse", "injection", "question", "override.ignore_rules")

    async def refuse(request, data=None, dataset_name=None) -> str:
        raise ArmorRefusal([decision])

    env.orchestrator.start = refuse
    async with env.client() as client:
        response = await client.post("/api/runs", json={"case_id": "a"})
    assert response.status_code == 400
    assert "Armor refused the run" in response.json()["detail"]
    records = [
        json.loads(line)
        for line in global_audit_path(env.app.state.settings).read_text().splitlines()
    ]
    refused = [r for r in records if r["kind"] == "armor.screen"]
    assert refused[0]["decision"] == "deny"
    assert refused[0]["principal"] == "caller://anonymous"
    assert refused[0]["data"]["action"] == "refuse" and refused[0]["data"]["field"] == "question"
