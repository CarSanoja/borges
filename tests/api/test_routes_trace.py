from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from borges.api.app import create_app
from borges.config import Settings
from borges.telemetry.audit_log import AuditLog
from borges.telemetry.trace_tree import NO_SPANS_REASON


class Store:
    def __init__(self, ids: set[str]) -> None:
        self.ids = ids

    def exists(self, run_id: str) -> bool:
        return run_id in self.ids

    def meta(self, run_id: str) -> dict[str, Any]:
        return {"run_id": run_id, "case_id": "demo", "public": True}


class Card:
    id = "demo"
    has_recording = True
    live_recording = None


class Event:
    run_id = "r_recorded"


class Registry:
    def list(self) -> list[Card]:
        return [Card()]

    def recording(self, case_id: str, source: str = "scripted") -> list[Event]:
        return [Event()]


def span(span_id: str, parent: str | None, kind: str, start: int) -> dict[str, Any]:
    return {
        "name": kind,
        "kind": kind,
        "trace_id": "t" * 32,
        "span_id": span_id,
        "parent_span_id": parent,
        "start_ns": start,
        "end_ns": start + 5_000_000,
        "status": "UNSET",
        "attributes": {"gen_ai.request.model": "m"} if kind == "model_call" else {},
    }


@pytest.fixture
def env(tmp_path: Path):
    settings = Settings(
        _env_file=None, borges_home=tmp_path / "home", borges_runs_dir=tmp_path / "runs"
    )
    traced = settings.borges_runs_dir / "r_traced"
    traced.mkdir(parents=True)
    spans = [
        span("a" * 16, None, "run", 1),
        span("b" * 16, "a" * 16, "stage", 2),
        span("c" * 16, "b" * 16, "model_call", 3),
    ]
    (traced / "spans.jsonl").write_text("\n".join(json.dumps(s) for s in spans) + "\n")
    AuditLog(traced / "audit.jsonl").append(
        "model.call", run_id="r_traced", span_id="c" * 16, data={"tokens_in": 3}
    )
    (settings.borges_runs_dir / "r_old").mkdir()
    app = create_app(
        settings=settings,
        orchestrator=object(),
        registry=Registry(),
        store=Store({"r_traced", "r_old"}),
        bus=object(),
    )
    return app, traced


def client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def test_trace_returns_the_span_tree_with_linked_audit(env) -> None:
    app, _ = env
    async with client(app) as http:
        response = await http.get("/api/runs/r_traced/trace")
    body = response.json()
    assert response.status_code == 200 and body["span_count"] == 3 and body["reason"] is None
    run = body["roots"][0]
    assert run["kind"] == "run" and run["children"][0]["children"][0]["kind"] == "model_call"
    call = run["children"][0]["children"][0]
    assert call["audit"][0]["data"] == {"tokens_in": 3}
    assert body["spans_by_kind"] == {"run": 1, "stage": 1, "model_call": 1}
    assert body["audit_chain"]["ok"] is True


async def test_audit_endpoint_reports_chain_status(env) -> None:
    app, traced = env
    async with client(app) as http:
        ok = (await http.get("/api/runs/r_traced/audit")).json()
        text = (traced / "audit.jsonl").read_text().replace('"tokens_in":3', '"tokens_in":9')
        (traced / "audit.jsonl").write_text(text)
        broken = (await http.get("/api/runs/r_traced/audit")).json()
    assert ok["chain"]["ok"] is True and len(ok["records"]) == 1
    assert broken["chain"]["ok"] is False and broken["chain"]["broken_seq"] == 1


async def test_run_without_spans_degrades_gracefully(env) -> None:
    app, _ = env
    async with client(app) as http:
        trace = (await http.get("/api/runs/r_old/trace")).json()
        audit = (await http.get("/api/runs/r_old/audit")).json()
    assert trace["roots"] == [] and trace["reason"] == NO_SPANS_REASON
    assert audit["records"] == [] and audit["chain"]["exists"] is False


async def test_recorded_case_run_returns_empty_tree_with_reason(env) -> None:
    app, _ = env
    async with client(app) as http:
        trace = await http.get("/api/runs/r_recorded/trace")
        audit = await http.get("/api/runs/r_recorded/audit")
    assert trace.status_code == 200 and trace.json()["roots"] == []
    assert trace.json()["reason"] == NO_SPANS_REASON
    assert audit.status_code == 200 and audit.json()["records"] == []


async def test_unknown_run_is_404(env) -> None:
    app, _ = env
    async with client(app) as http:
        assert (await http.get("/api/runs/nope/trace")).status_code == 404
        assert (await http.get("/api/runs/nope/audit")).status_code == 404
