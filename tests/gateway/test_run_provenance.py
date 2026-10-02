from __future__ import annotations

from pathlib import Path

import pytest

from borges.cases.registry import CaseRegistry
from borges.gateway.policy_load import policy_for
from borges.runs import orchestrator as orchestrator_module
from borges.runs.bus import EventBus
from borges.runs.models import RunRequest
from borges.runs.orchestrator import RunOrchestrator
from borges.runs.store import RunStore
from borges.telemetry.audit_verify import read_records
from borges.telemetry.run_telemetry import run_audit_path
from tests.telemetry.conftest import make_settings


def orchestrator(tmp_path: Path) -> tuple[RunOrchestrator, RunStore]:
    settings = make_settings(tmp_path)
    store = RunStore(settings.borges_runs_dir)
    return RunOrchestrator(
        settings, store, EventBus(store), CaseRegistry(settings.borges_cases_dir)
    ), store


async def test_the_policy_sha_is_in_run_provenance(tmp_path: Path) -> None:
    runs, store = orchestrator(tmp_path)
    snapshot = await runs.execute("r_pv", RunRequest(case_id="checkout_ab", llm="scripted"))
    assert snapshot.status == "completed"
    sha = policy_for(runs.settings).sha
    assert snapshot.agents.policy_sha == sha
    judge = next(a for a in snapshot.agents.agents if a.agent_id == "judge")
    assert judge.policy_sha and judge.policy_sha != sha
    assert store.meta("r_pv")["agents"]["policy_sha"] == sha


async def test_a_run_without_agent_tokens_fails_closed_with_a_clear_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(orchestrator_module, "mint_identity", lambda settings, run_id: None)
    runs, _ = orchestrator(tmp_path)
    snapshot = await runs.execute("r_nt", RunRequest(case_id="checkout_ab", llm="scripted"))
    assert snapshot.status == "failed"
    assert "gateway denied (identity)" in snapshot.error
    records = read_records(run_audit_path(runs.settings, "r_nt"))
    assert any(r.kind == "gateway.deny" and r.decision == "deny" for r in records)


async def test_an_unreadable_policy_stops_the_run_before_any_call(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, borges_gateway_policy=tmp_path / "gone.json")
    store = RunStore(settings.borges_runs_dir)
    runs = RunOrchestrator(
        settings, store, EventBus(store), CaseRegistry(settings.borges_cases_dir)
    )
    snapshot = await runs.execute("r_np", RunRequest(case_id="checkout_ab", llm="scripted"))
    assert snapshot.status == "failed" and "gateway policy" in snapshot.error
