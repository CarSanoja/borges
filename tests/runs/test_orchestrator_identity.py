from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.cases.registry import CaseRegistry
from borges.runs import orchestrator_identity
from borges.runs.bus import EventBus
from borges.runs.models import RunRequest
from borges.runs.orchestrator import RunOrchestrator
from borges.runs.orchestrator_identity import mint_identity
from borges.runs.store import RunStore
from borges.telemetry.audit_global_verify import verify_global
from borges.telemetry.audit_verify import read_records
from borges.telemetry.run_telemetry import global_audit_path, run_audit_path
from tests.telemetry.conftest import make_settings


async def test_a_run_mints_tokens_and_anchors_the_global_log(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    store = RunStore(settings.borges_runs_dir)
    runs = RunOrchestrator(
        settings, store, EventBus(store), CaseRegistry(settings.borges_cases_dir)
    )
    snapshot = await runs.execute("r_id", RunRequest(case_id="checkout_ab", llm="scripted"))
    assert snapshot.status == "completed" and snapshot.flip.universe_id == "u_4e00fbb461"
    records = read_records(run_audit_path(settings, "r_id"))
    minted = next(r for r in records if r.kind == "identity.agent_tokens.minted")
    assert minted.decision == "allow" and "planner" in minted.data["agents"]
    assert "." not in json.dumps(minted.data["agents"])
    model_calls = [r for r in records if r.kind == "model.call"]
    assert model_calls and all(r.principal.startswith("agent://borges/") for r in model_calls)
    report = verify_global(global_audit_path(settings), None)
    assert report.ok and report.anchored == report.records


def test_token_minting_failure_does_not_break_a_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*args, **kwargs):
        raise RuntimeError("no fleet")

    monkeypatch.setattr(orchestrator_identity, "mint_run_identity", boom)
    assert mint_identity(make_settings(tmp_path), "r") is None
