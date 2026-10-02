from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from borges.cases.registry import CaseRegistry
from borges.config import REPO_ROOT, Settings
from borges.runs.bus import EventBus
from borges.runs.orchestrator import RunOrchestrator
from borges.runs.store import RunStore
from borges.runtime.runtime import Runtime


@dataclass
class Rig:
    settings: Settings
    store: RunStore
    bus: EventBus
    orchestrator: RunOrchestrator
    runtime: Runtime


def make_settings(root: Path, **overrides) -> Settings:
    fields = {
        "nebius_api_key": None,
        "borges_llm": "scripted",
        "borges_backend": "local",
        "borges_home": root / "home",
        "borges_runs_dir": root / "runs",
        "borges_cases_dir": REPO_ROOT / "cases",
        "borges_runtime_poll_s": 0.05,
        "borges_job_lease_s": 5.0,
        "borges_job_backoff_s": 0.05,
    }
    return Settings(_env_file=None, **{**fields, **overrides})


def make_rig(root: Path, cases_dir: Path | None = None, **overrides) -> Rig:
    settings = make_settings(root, **overrides)
    if cases_dir is not None:
        settings = settings.model_copy(update={"borges_cases_dir": cases_dir})
    store = RunStore(settings.borges_runs_dir)
    bus = EventBus(store)
    orchestrator = RunOrchestrator(settings, store, bus, CaseRegistry(settings.borges_cases_dir))
    return Rig(settings, store, bus, orchestrator, Runtime(settings, orchestrator, store, bus))


async def wait_for(predicate, timeout_s: float = 60.0, step_s: float = 0.02) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_s
    while not predicate():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("condition not reached in time")
        await asyncio.sleep(step_s)
