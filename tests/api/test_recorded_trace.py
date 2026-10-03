from __future__ import annotations

import json
from pathlib import Path

import httpx

from borges.api.app import create_app
from borges.cases.registry import CaseRegistry
from borges.config import Settings
from borges.telemetry.audit_log import AuditLog
from tests.live_cases import LIVE_RUN_ID, make_cases_dir


class Store:
    def exists(self, run_id: str) -> bool:
        return False


def span(span_id: str, parent: str | None, kind: str, start: int) -> dict:
    return {
        "name": kind,
        "kind": kind,
        "trace_id": "t" * 32,
        "span_id": span_id,
        "parent_span_id": parent,
        "start_ns": start,
        "end_ns": start + 1000,
        "status": "UNSET",
        "attributes": {},
    }


def make_app(tmp_path: Path, traced: bool):
    cases = make_cases_dir(tmp_path)
    live = cases / "checkout_ab" / "recorded-live"
    if traced:
        spans = [span("a" * 16, None, "run", 1), span("b" * 16, "a" * 16, "stage", 2)]
        (live / "spans.jsonl").write_text("\n".join(json.dumps(s) for s in spans) + "\n")
        AuditLog(live / "audit.jsonl").append(
            "model.call", run_id=LIVE_RUN_ID, span_id="b" * 16, data={"n": 1}
        )
    settings = Settings(
        _env_file=None,
        borges_home=tmp_path / "home",
        borges_runs_dir=tmp_path / "runs",
        borges_cases_dir=cases,
    )
    return create_app(
        settings=settings, orchestrator=object(), registry=CaseRegistry(cases), store=Store()
    )


async def get(app, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as http:
        return await http.get(path)


async def test_recorded_run_with_spans_serves_its_trace_and_chain(tmp_path: Path) -> None:
    app = make_app(tmp_path, traced=True)
    trace = (await get(app, f"/api/runs/{LIVE_RUN_ID}/trace")).json()
    assert trace["span_count"] == 2 and trace["reason"] is None
    assert trace["audit_chain"]["ok"] is True
    assert trace["audit_chain"]["path"] == f"{LIVE_RUN_ID}/audit.jsonl"
    audit = (await get(app, f"/api/runs/{LIVE_RUN_ID}/audit")).json()
    assert audit["chain"]["ok"] is True and len(audit["records"]) == 1


async def test_recorded_run_without_spans_explains_why(tmp_path: Path) -> None:
    app = make_app(tmp_path, traced=False)
    trace = (await get(app, f"/api/runs/{LIVE_RUN_ID}/trace")).json()
    assert trace["roots"] == [] and trace["reason"]


async def test_cards_list_which_recordings_have_spans(tmp_path: Path) -> None:
    traced = (await get(make_app(tmp_path / "a", True), "/api/cases/checkout_ab")).json()
    bare = (await get(make_app(tmp_path / "b", False), "/api/cases/checkout_ab")).json()
    assert traced["traced_sources"] == ["live"]
    assert bare["traced_sources"] == []
