from __future__ import annotations

import json
from pathlib import Path

from borges.cases.registry import CaseRegistry
from borges.runs.bus import EventBus
from borges.runs.models import RunRequest
from borges.runs.orchestrator import RunOrchestrator
from borges.runs.store import RunStore
from borges.telemetry.run_telemetry import run_audit_path
from tests.telemetry.conftest import make_settings


async def scripted(tmp_path: Path):
    settings = make_settings(tmp_path)
    store = RunStore(settings.borges_runs_dir)
    runs = RunOrchestrator(
        settings, store, EventBus(store), CaseRegistry(settings.borges_cases_dir)
    )
    snapshot = await runs.execute(
        "r_fleet", RunRequest(case_id="checkout_ab", llm="scripted", max_universes=3)
    )
    return settings, store, snapshot


async def test_run_records_agent_versions_everywhere(tmp_path: Path) -> None:
    settings, store, snapshot = await scripted(tmp_path)
    assert snapshot.status == "completed"
    meta = store.meta("r_fleet")["agents"]
    assert len(meta["agents"]) == 12 and len(meta["registry_sha"]) == 64
    started = next(e for e in store.events("r_fleet") if e.type == "run.started")
    assert started.data["agents"] == meta
    assert snapshot.agents is not None and snapshot.agents.registry_sha == meta["registry_sha"]
    assert snapshot.report is not None and snapshot.report.agents == snapshot.agents
    judge = next(a for a in meta["agents"] if a["agent_id"] == "judge")
    assert judge["version"] == "2.0.0" and judge["approval"] == "approved"
    assert judge["model_id"] == "scripted" and len(judge["definition_sha"]) == 64


async def test_run_audit_log_carries_the_provenance(tmp_path: Path) -> None:
    settings, store, _ = await scripted(tmp_path)
    lines = run_audit_path(settings, "r_fleet").read_text().splitlines()
    records = [json.loads(line) for line in lines]
    provenance = [r for r in records if r["kind"] == "registry.provenance"]
    assert len(provenance) == 1
    shas = {a["agent_id"]: a["definition_sha"] for a in provenance[0]["data"]["agents"]}
    meta = store.meta("r_fleet")["agents"]["agents"]
    assert shas == {a["agent_id"]: a["definition_sha"] for a in meta}
