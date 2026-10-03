from __future__ import annotations

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from borges.bench.blade_adapter import AdaptedCase, to_request
from borges.config import Settings
from borges.runs.models import RunSnapshot

ARMS = ("planner", "adversary")
KEEP = ("events.jsonl", "meta.json")


@contextmanager
def adversary_disabled() -> Iterator[None]:
    from borges.runs import pipeline_search

    async def skipped(*args: Any, **kwargs: Any) -> None:
        return None

    original = pipeline_search.run_adversary
    pipeline_search.run_adversary = skipped
    try:
        yield
    finally:
        pipeline_search.run_adversary = original


def run_settings(base: Settings, out: Path, cases_dir: Path, repeat: int, label: str) -> Settings:
    return base.model_copy(
        update={
            "borges_cases_dir": cases_dir,
            "borges_runs_dir": out / "runs" / label,
            "borges_home": out / "home" / f"repeat{repeat}",
            "otel_exporter_otlp_endpoint": None,
            "borges_memory": False,
        }
    )


def prune_run(settings: Settings, run_id: str) -> None:
    directory = settings.borges_runs_dir / run_id
    if not directory.is_dir():
        return
    for path in directory.iterdir():
        if path.name in KEEP:
            continue
        shutil.rmtree(path) if path.is_dir() else path.unlink()


async def run_arm(
    settings: Settings,
    adapted: AdaptedCase,
    arm: str,
    llm: str,
    repeat: int,
    max_universes: int,
) -> RunSnapshot:
    from borges.cli_runtime import execute_run
    from borges.runs.orchestrator import new_run_id

    request = to_request(adapted, llm, max_universes)
    run_id = new_run_id()
    try:
        if arm == "planner":
            with adversary_disabled():
                return await execute_run(settings, run_id, request, False)
        return await execute_run(settings, run_id, request, False)
    finally:
        prune_run(settings, run_id)
