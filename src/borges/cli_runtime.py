from __future__ import annotations

import shutil
from pathlib import Path

from borges.config import Settings
from borges.runs.models import RunRequest, RunSnapshot


def list_cases(settings: Settings) -> list:
    from borges.cases.registry import CaseRegistry

    return CaseRegistry(settings.borges_cases_dir).list()


async def execute_run(
    settings: Settings, run_id: str, request: RunRequest, record: bool
) -> RunSnapshot:
    from borges.cases.registry import CaseRegistry
    from borges.runs.bus import EventBus
    from borges.runs.orchestrator import RunOrchestrator
    from borges.runs.store import RunStore

    store = RunStore(settings.borges_runs_dir)
    bus = EventBus(store)
    registry = CaseRegistry(settings.borges_cases_dir)
    extra = {}
    if record:
        extra["record_dir"] = settings.borges_runs_dir / run_id / "fixtures"
    orchestrator = RunOrchestrator(settings, store, bus, registry, **extra)
    return await orchestrator.execute(run_id, request)


def load_snapshot(settings: Settings, run_id: str) -> RunSnapshot:
    from borges.runs.store import RunStore

    return RunStore(settings.borges_runs_dir).snapshot(run_id)


def copy_recording(settings: Settings, run_id: str, case_id: str) -> Path:
    source = settings.borges_runs_dir / run_id / "events.jsonl"
    if not source.is_file():
        raise FileNotFoundError(f"no event log at {source}")
    target = settings.borges_cases_dir / case_id / "recorded" / "events.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target
