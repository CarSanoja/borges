from __future__ import annotations

import sys
import types
from collections.abc import AsyncIterator

import httpx
import pytest

from borges.analysis.models import DecisionRule
from borges.api.app import create_app
from borges.cases.models import CaseCard
from borges.config import Settings
from borges.runs.events import Event


def card(case_id: str, recording: bool) -> CaseCard:
    return CaseCard(
        id=case_id,
        title=case_id,
        subtitle="s",
        question="q",
        decision_rule=DecisionRule(metric="m"),
        n_rows=10,
        has_recording=recording,
    )


class FakeRegistry:
    def __init__(self) -> None:
        self.cards = {"a": card("a", True), "b": card("b", False)}
        self.events = [
            Event(seq=0, ts=0, run_id="r", type="stage"),
            Event(seq=1, ts=0, run_id="r", type="run.finished"),
        ]

    def list(self) -> list[CaseCard]:
        return list(self.cards.values())

    def card(self, case_id: str) -> CaseCard:
        return self.cards[case_id]

    def recording(self, case_id: str, source: str = "scripted") -> list[Event] | None:
        return self.events if case_id == "a" else None


@pytest.fixture
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> httpx.AsyncClient:
    speeds: list[float] = []

    async def replay_events(events: list[Event], speed: float) -> AsyncIterator[Event]:
        speeds.append(speed)
        for event in events:
            yield event

    module = types.ModuleType("borges.runs.replay")
    module.replay_events = replay_events
    module.speeds = speeds
    monkeypatch.setitem(sys.modules, "borges.runs.replay", module)
    app = create_app(settings=Settings(borges_home=tmp_path), registry=FakeRegistry())
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def test_list_cases(client: httpx.AsyncClient) -> None:
    async with client:
        body = (await client.get("/api/cases")).json()
    assert [c["id"] for c in body] == ["a", "b"]


async def test_get_case_and_404(client: httpx.AsyncClient) -> None:
    async with client:
        assert (await client.get("/api/cases/a")).json()["id"] == "a"
        assert (await client.get("/api/cases/zzz")).status_code == 404


async def test_recording_streams_events(client: httpx.AsyncClient) -> None:
    async with client:
        response = await client.get("/api/cases/a/recording?speed=8")
    assert response.status_code == 200
    assert "event: run.finished" in response.text
    assert sys.modules["borges.runs.replay"].speeds == [8.0]


async def test_recording_missing_is_404(client: httpx.AsyncClient) -> None:
    async with client:
        assert (await client.get("/api/cases/b/recording")).status_code == 404
        assert (await client.get("/api/cases/zzz/recording")).status_code == 404
