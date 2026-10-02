from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import pytest

from borges.cli_runtime import execute_run
from borges.config import REPO_ROOT, Settings
from borges.runs.models import RunRequest, RunSnapshot
from borges.runs.store import RunStore


@dataclass
class ScriptedRun:
    settings: Settings
    run_id: str
    snapshot: RunSnapshot
    run_dir: Path

    @property
    def store(self) -> RunStore:
        return RunStore(self.settings.borges_runs_dir)


def make_settings(root: Path, **extra: object) -> Settings:
    return Settings(
        _env_file=None,
        borges_home=root / "home",
        borges_runs_dir=root / "runs",
        borges_cases_dir=REPO_ROOT / "cases",
        otel_exporter_otlp_endpoint=None,
        **extra,
    )


@pytest.fixture(scope="session")
def scripted_run(tmp_path_factory: pytest.TempPathFactory) -> ScriptedRun:
    root = tmp_path_factory.mktemp("telemetry_run")
    settings = make_settings(root)
    run_id = "r_trace_checkout"
    snapshot = asyncio.run(
        execute_run(settings, run_id, RunRequest(case_id="checkout_ab", llm="scripted"), False)
    )
    return ScriptedRun(settings, run_id, snapshot, settings.borges_runs_dir / run_id)
