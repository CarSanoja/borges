from __future__ import annotations

from pathlib import Path

import pytest

from borges.config import Settings
from borges.sandbox.backend import Checkpoint, ExecResult
from borges.telemetry import hooks
from borges.telemetry.audit_verify import read_records
from borges.telemetry.instrumented_backend import InstrumentedBackend, instrument_backend
from borges.telemetry.run_telemetry import RunTelemetry
from borges.telemetry.scopes import option_span
from borges.telemetry.trace_tree import read_spans


class FakeBackend:
    name = "fake"

    def __init__(self, exit_code: int = 0, fail: bool = False) -> None:
        self.exit_code = exit_code
        self.fail = fail
        self.closed = False

    async def root(self, files):
        return Checkpoint("c0", None, "fake")

    async def run(self, parent, command, files=None, timeout_s=120.0):
        if self.fail:
            raise RuntimeError("sandbox exploded")
        child = Checkpoint("c1", parent.id, "fake")
        return ExecResult(child, self.exit_code, "out", "err", 0.25)

    async def read_file(self, checkpoint, path):
        return b"bytes"

    async def close(self):
        self.closed = True


def open_telemetry(tmp_path: Path) -> RunTelemetry:
    return RunTelemetry.open(
        Settings(_env_file=None, borges_home=tmp_path / "home"), "r1", tmp_path / "run"
    )


async def test_exec_span_and_audit_record_link_checkpoints(tmp_path: Path) -> None:
    telemetry = open_telemetry(tmp_path)
    backend = InstrumentedBackend(FakeBackend())
    with hooks.bound(telemetry), telemetry.span("run", "run r1"):
        root = await backend.root({"data.parquet": b"x"})
        with option_span("step", "s1", "a"):
            result = await backend.run(root, ["python", "step.py"], timeout_s=5)
    telemetry.close()
    assert result.checkpoint.id == "c1" and backend.name == "fake"
    span = next(
        s for s in read_spans(tmp_path / "run" / "spans.jsonl") if s["kind"] == "sandbox_exec"
    )
    assert span["attributes"]["borges.checkpoint.parent"] == "c0"
    assert span["attributes"]["borges.checkpoint.child"] == "c1"
    assert span["attributes"]["borges.sandbox.exit_code"] == 0
    assert span["attributes"]["borges.step_id"] == "s1"
    record = next(
        r for r in read_records(tmp_path / "run" / "audit.jsonl") if r.kind == "sandbox.exec"
    )
    assert record.span_id == span["span_id"]
    assert record.data["parent_checkpoint"] == "c0" and record.data["child_checkpoint"] == "c1"
    assert record.data["step_id"] == "s1" and record.data["option_id"] == "a"
    assert record.data["duration_s"] == 0.25 and record.data["outcome"] == "ok"


async def test_failed_exit_and_exception_are_recorded(tmp_path: Path) -> None:
    telemetry = open_telemetry(tmp_path)
    with hooks.bound(telemetry), telemetry.span("run", "run r1"):
        failing = InstrumentedBackend(FakeBackend(exit_code=2))
        await failing.run(Checkpoint("c0", None, "fake"), ["python", "x.py"])
        exploding = InstrumentedBackend(FakeBackend(fail=True))
        with pytest.raises(RuntimeError):
            await exploding.run(Checkpoint("c0", None, "fake"), ["python", "x.py"])
    telemetry.close()
    outcomes = [
        r.data["outcome"]
        for r in read_records(tmp_path / "run" / "audit.jsonl")
        if r.kind == "sandbox.exec"
    ]
    assert outcomes == ["failed", "error"]


async def test_wrapper_is_transparent_without_telemetry() -> None:
    inner = FakeBackend()
    backend = instrument_backend(inner)
    root = await backend.root({})
    assert (await backend.run(root, ["python"])).ok
    assert await backend.read_file(root, "f") == b"bytes"
    await backend.close()
    assert inner.closed
    assert instrument_backend(backend) is backend


async def test_backend_wrapper_blocks_direct_access_to_provider_methods() -> None:
    backend = InstrumentedBackend(FakeBackend())
    with pytest.raises(AttributeError, match="gateway"):
        backend.__getattr__("close")
    assert backend.closed is False


async def test_backend_calls_are_gated_and_carry_the_policy(tmp_path: Path) -> None:
    from borges.gateway.core import build_gateway
    from borges.gateway.errors import GatewayDenied
    from borges.identity.run_identity import mint_run_identity

    settings = Settings(_env_file=None, borges_home=tmp_path / "home")
    gateway = build_gateway(settings, "r1", mint_run_identity(settings, "r1"))
    backend = InstrumentedBackend(FakeBackend(), gateway)
    telemetry = open_telemetry(tmp_path)
    with hooks.bound(telemetry), telemetry.span("run", "run r1"):
        root = await backend.root({"data.parquet": b"x"})
        with pytest.raises(GatewayDenied):
            await backend.run(root, ["bash", "-c", "id"], files={"steps/a.py": b"x"})
        code = "def apply(df, ctx):\n    return df\n"
        gateway.evidence.record(code)
        result = await backend.run(
            root, ["python", "steps/a.py"], files={"steps/a.py": code.encode()}
        )
    telemetry.close()
    assert result.ok
    records = read_records(tmp_path / "run" / "audit.jsonl")
    execs = [r for r in records if r.kind == "sandbox.exec"]
    assert [(r.decision, r.data["outcome"]) for r in execs] == [("deny", "denied"), ("allow", "ok")]
    assert execs[1].principal == "agent://borges/harness"
    assert execs[1].data["policy_sha"] == gateway.policy_sha
