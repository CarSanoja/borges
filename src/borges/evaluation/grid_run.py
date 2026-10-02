from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from borges.analysis.models import AnalysisPlan
from borges.garden.executor import GardenExecutor
from borges.garden.models import Garden
from borges.sandbox.backend import BranchBackend

ProgressFn = Callable[[int, int], None]


@dataclass(frozen=True)
class GridRun:
    garden: Garden
    wall_s: float
    checkpoints: int
    prefix_sharing: bool


async def run_grid(
    backend: BranchBackend,
    plan: AnalysisPlan,
    data: bytes,
    universes: list[dict[str, str]],
    concurrency: int = 6,
    reuse_prefixes: bool = True,
    progress: ProgressFn | None = None,
) -> GridRun:
    import asyncio

    started = time.monotonic()
    executor = GardenExecutor(
        backend, plan, data, concurrency=concurrency, reuse_prefixes=reuse_prefixes
    )
    await executor.setup()
    garden = Garden()
    baseline = await executor.run_universe(plan.default_choices(), "baseline")
    garden.add(baseline)
    garden.baseline_id = baseline.id
    if baseline.status != "done":
        raise RuntimeError(f"the baseline universe failed: {baseline.error}")
    rest = [u for u in universes if u != plan.default_choices()]
    done = 1
    total = len(rest) + 1

    async def one(choices: dict[str, str]) -> None:
        nonlocal done
        universe = await executor.run_universe(choices, "combination")
        garden.add(universe)
        done += 1
        if progress is not None and (done % 25 == 0 or done == total):
            progress(done, total)

    await asyncio.gather(*(one(c) for c in rest))
    return GridRun(garden, time.monotonic() - started, executor.checkpoints_created, reuse_prefixes)
