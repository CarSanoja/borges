from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

from borges.runs.models import RunRequest
from borges.runtime.runtime import Runtime
from tests.runs.engine_fakes import Scenario, install
from tests.runs.fakes import Rig, make_rig

REQUEST = RunRequest(case_id="demo", llm="scripted")


@dataclass
class FakeRuntime:
    rig: Rig
    scenario: Scenario
    runtime: Runtime


def make_fake_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **settings) -> FakeRuntime:
    scenario = Scenario()
    install(monkeypatch, scenario)
    rig = make_rig(tmp_path)
    updated = rig.orchestrator.settings.model_copy(
        update={
            "borges_runtime_poll_s": 0.05,
            "borges_job_lease_s": 5.0,
            "borges_job_backoff_s": 0.01,
            **settings,
        }
    )
    rig.orchestrator.settings = updated
    return FakeRuntime(rig, scenario, Runtime(updated, rig.orchestrator, rig.store, rig.bus))


def transient_error() -> Exception:
    return httpx.ConnectError("provider unreachable")
