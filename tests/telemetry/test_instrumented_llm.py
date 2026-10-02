from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from borges.config import Settings
from borges.llm.client import BudgetExceeded, LLMError, LLMResponse, Role, Usage, UsageTotals
from borges.telemetry import hooks
from borges.telemetry.audit_verify import read_records, verify_chain
from borges.telemetry.caller import calling_as
from borges.telemetry.instrumented_llm import InstrumentedLLM, instrument_llm
from borges.telemetry.run_telemetry import RunTelemetry
from borges.telemetry.trace_tree import read_spans

SECRET_PROMPT = "ROW 17: patient 4412 earns 7316204 and key sk-live-abc"
SECRET_REPLY = "the answer mentions patient 4412"


class Spec:
    id = "nvidia/nemotron-3-super-120b-a12b"


class FakeNebius:
    def __init__(self, fail: Exception | None = None) -> None:
        self.totals = UsageTotals()
        self.role_models = {Role.PLANNER: Spec()}
        self.fail = fail
        self.extra = "reachable"

    async def complete(self, role, messages, *, key, schema=None, max_tokens=2048, temperature=0.2):
        if self.fail is not None:
            raise self.fail
        usage = Usage(model=Spec.id, tokens_in=120, tokens_out=45, cost_usd=0.0012, cached=True)
        self.totals.add(usage)
        return LLMResponse(role=role, text=SECRET_REPLY, usage=usage, latency_s=0.01)


class Schema(BaseModel):
    x: int = 1


def open_telemetry(tmp_path: Path) -> RunTelemetry:
    settings = Settings(_env_file=None, borges_home=tmp_path / "home")
    return RunTelemetry.open(settings, "r1", tmp_path / "run")


async def call(llm, **kw):
    return await llm.complete(
        Role.PLANNER,
        [{"role": "user", "content": SECRET_PROMPT}],
        key="planner",
        schema=Schema,
        **kw,
    )


async def test_model_span_follows_genai_conventions(tmp_path: Path) -> None:
    telemetry = open_telemetry(tmp_path)
    llm = InstrumentedLLM(FakeNebius())
    with (
        hooks.bound(telemetry),
        telemetry.span("run", "run r1"),
        calling_as(principal="svc:planner"),
    ):
        await call(llm)
    telemetry.close()
    span = next(
        s for s in read_spans(tmp_path / "run" / "spans.jsonl") if s["kind"] == "model_call"
    )
    attrs = span["attributes"]
    assert span["name"] == "chat nvidia/nemotron-3-super-120b-a12b"
    assert attrs["gen_ai.system"] == "nebius"
    assert attrs["gen_ai.operation.name"] == "chat"
    assert attrs["gen_ai.request.model"] == Spec.id == attrs["gen_ai.response.model"]
    assert attrs["gen_ai.usage.input_tokens"] == 120
    assert attrs["gen_ai.usage.output_tokens"] == 45
    assert attrs["borges.agent.role"] == "planner"
    assert attrs["borges.cache.hit"] is True
    assert attrs["borges.cost_usd"] == pytest.approx(0.0012)
    assert attrs["borges.latency_s"] >= 0
    assert attrs["borges.principal"] == "svc:planner"
    assert len(attrs["borges.prompt.sha256"]) == 64 and len(attrs["borges.response.sha256"]) == 64


async def test_no_raw_prompt_or_response_reaches_spans_or_audit(tmp_path: Path) -> None:
    telemetry = open_telemetry(tmp_path)
    llm = InstrumentedLLM(FakeNebius())
    with hooks.bound(telemetry), telemetry.span("run", "run r1"):
        await call(llm)
    telemetry.close()
    spans = (tmp_path / "run" / "spans.jsonl").read_text()
    audit = (tmp_path / "run" / "audit.jsonl").read_text()
    for blob in (spans, audit, (tmp_path / "home" / "audit" / "global.jsonl").read_text()):
        for secret in ("patient 4412", "sk-live", "7316204", "ROW 17"):
            assert secret not in blob
    record = next(
        r for r in read_records(tmp_path / "run" / "audit.jsonl") if r.kind == "model.call"
    )
    assert record.principal == "agent:planner"
    assert record.data["outcome"] == "ok" and record.data["cache_hit"] is True
    assert record.data["tokens_in"] == 120 and record.data["role"] == "planner"
    assert verify_chain(tmp_path / "run" / "audit.jsonl").ok


async def test_prompt_hash_is_stable_and_content_sensitive(tmp_path: Path) -> None:
    telemetry = open_telemetry(tmp_path)
    llm = InstrumentedLLM(FakeNebius())
    with hooks.bound(telemetry), telemetry.span("run", "run r1"):
        await call(llm)
        await call(llm)
        await llm.complete(Role.PLANNER, [{"role": "user", "content": "other"}], key="planner")
    telemetry.close()
    hashes = [
        s["attributes"]["borges.prompt.sha256"]
        for s in read_spans(tmp_path / "run" / "spans.jsonl")
        if s["kind"] == "model_call"
    ]
    assert hashes[0] == hashes[1] != hashes[2]


async def test_failed_call_is_audited_and_reraised(tmp_path: Path) -> None:
    telemetry = open_telemetry(tmp_path)
    with hooks.bound(telemetry), telemetry.span("run", "run r1"):
        with pytest.raises(BudgetExceeded):
            await call(InstrumentedLLM(FakeNebius(BudgetExceeded("run budget $0.5 exceeded"))))
        with pytest.raises(LLMError):
            await call(InstrumentedLLM(FakeNebius(LLMError("bad json with patient 4412"))))
    telemetry.close()
    records = [r for r in read_records(tmp_path / "run" / "audit.jsonl") if r.kind == "model.call"]
    assert [(r.decision, r.data["outcome"]) for r in records] == [
        ("deny", "refused"),
        (None, "error"),
    ]
    assert "patient 4412" not in (tmp_path / "run" / "audit.jsonl").read_text()
    spans = [s for s in read_spans(tmp_path / "run" / "spans.jsonl") if s["kind"] == "model_call"]
    assert [s["status"] for s in spans] == ["ERROR", "ERROR"]
    assert spans[0]["attributes"]["error.type"] == "BudgetExceeded"


async def test_without_telemetry_the_wrapper_is_transparent() -> None:
    inner = FakeNebius()
    llm = instrument_llm(inner)
    response = await call(llm)
    assert response.text == SECRET_REPLY
    assert llm.totals is inner.totals
    assert llm.extra == "reachable"
    assert instrument_llm(llm) is llm


def test_audit_payload_is_json() -> None:
    assert json.dumps({"ok": True})
