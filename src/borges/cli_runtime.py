from __future__ import annotations

import shutil
from pathlib import Path

from borges.cases.live_summary import LIVE_FOLDER
from borges.cases.recording_stamp import stamp_copy
from borges.config import Settings
from borges.runs.models import RunRequest, RunSnapshot

LIVE_LLMS = ("nebius", "local")
TRACE_FILES = ("spans.jsonl", "audit.jsonl")


def list_cases(settings: Settings) -> list:
    from borges.cases.registry import CaseRegistry

    return CaseRegistry(settings.borges_cases_dir).list()


async def execute_run(
    settings: Settings, run_id: str, request: RunRequest, record: bool
) -> RunSnapshot:
    from borges.cases.registry import CaseRegistry
    from borges.fleet.enforcement import enforce_registry
    from borges.runs.bus import EventBus
    from borges.runs.orchestrator import RunOrchestrator
    from borges.runs.store import RunStore

    enforce_registry(settings, request.llm or settings.borges_llm)
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


def copy_recording(settings: Settings, run_id: str, case_id: str, llm: str = "scripted") -> Path:
    source = settings.borges_runs_dir / run_id / "events.jsonl"
    if not source.is_file():
        raise FileNotFoundError(f"no event log at {source}")
    folder = LIVE_FOLDER if llm in LIVE_LLMS else "recorded"
    target = settings.borges_cases_dir / case_id / folder / "events.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    for name in TRACE_FILES:
        sibling = source.parent / name
        if sibling.is_file():
            shutil.copyfile(sibling, target.parent / name)
        else:
            (target.parent / name).unlink(missing_ok=True)
    stamp_copy(source.parent, run_id, case_id, target.parent)
    return target


async def reproduce_recorded(
    settings: Settings, case_id: str, universe_id: str, source: str = "scripted"
):
    from borges.cases.registry import CaseRegistry
    from borges.runs.reproduce import Reproduction, reproduce_universe
    from borges.runs.state import fold
    from borges.sandbox.factory import make_backend

    registry = CaseRegistry(settings.borges_cases_dir)
    events = registry.recording(case_id, source)
    if not events:
        raise FileNotFoundError(f"case '{case_id}' has no committed {source} recording")
    snapshot = fold(events, events[0].run_id)
    if snapshot.plan is None:
        raise KeyError(f"the {source} recording of '{case_id}' has no plan")
    if universe_id not in snapshot.garden.universes:
        known = ", ".join(sorted(snapshot.garden.universes))
        raise KeyError(
            f"unknown universe '{universe_id}' in the {source} recording of case "
            f"'{case_id}'; known: {known}"
        )
    backend = make_backend(settings, "local")
    try:
        rep: Reproduction = await reproduce_universe(
            backend,
            snapshot.plan,
            registry.data_bytes(case_id),
            snapshot,
            universe_id,
            settings.borges_step_timeout_s,
        )
    finally:
        await backend.close()
    return snapshot.plan, rep
