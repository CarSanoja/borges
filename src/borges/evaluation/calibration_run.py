from __future__ import annotations

import asyncio
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from borges.config import Settings
from borges.evaluation.calibration_data import CASE_DIR, make_dataset, to_parquet_bytes
from borges.runs.models import RunRequest

INTERNAL_STEP = "internal_traffic"


@dataclass(frozen=True)
class Outcome:
    seed: int
    true_effect: float
    artefact: bool
    original_verdict: str
    flip_found: bool
    flip_kind: str | None
    n_changes: int
    flip_steps: list[str]
    baseline_estimate: float
    baseline_p: float
    universes: int
    seconds: float

    def to_dict(self) -> dict:
        return asdict(self)


def flip_kind(baseline_estimate: float, flipped_estimate: float) -> str:
    return "direction" if (baseline_estimate > 0) != (flipped_estimate > 0) else "significance"


async def _execute(settings: Settings, data: bytes):
    from borges.cases.registry import CaseRegistry
    from borges.runs.bus import EventBus
    from borges.runs.orchestrator import RunOrchestrator, new_run_id
    from borges.runs.store import RunStore

    store = RunStore(settings.borges_runs_dir)
    orchestrator = RunOrchestrator(
        settings, store, EventBus(store), CaseRegistry(settings.borges_cases_dir)
    )
    request = RunRequest(case_id="checkout_ab", llm="scripted", backend="local")
    return await orchestrator.execute(new_run_id(), request, data=data)


def run_one(
    seed: int,
    true_effect: float,
    artefact: bool,
    novelty_bump: float = 0.0,
    n_users: int | None = None,
) -> Outcome:
    import time

    started = time.monotonic()
    data = to_parquet_bytes(make_dataset(seed, true_effect, artefact, novelty_bump, n_users))
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(
            borges_llm="scripted",
            borges_backend="local",
            borges_cases_dir=CASE_DIR.parent,
            borges_runs_dir=Path(tmp) / "runs",
            borges_home=Path(tmp) / "home",
        )
        snapshot = asyncio.run(_execute(settings, data))
    if snapshot.status != "completed" or snapshot.report is None:
        raise RuntimeError(f"run failed: {snapshot.error}")
    flip = snapshot.flip
    kind = None
    steps: list[str] = []
    if flip is not None:
        kind = flip_kind(flip.baseline_result.estimate, flip.flipped_result.estimate)
        steps = [c.step_id for c in flip.changes]
    baseline = snapshot.garden.universes
    base = next(u for u in baseline.values() if u.kind == "baseline")
    return Outcome(
        seed=seed,
        true_effect=true_effect,
        artefact=artefact,
        original_verdict=snapshot.report.original_verdict,
        flip_found=flip is not None,
        flip_kind=kind,
        n_changes=len(flip.changes) if flip else 0,
        flip_steps=steps,
        baseline_estimate=base.result.estimate if base.result else float("nan"),
        baseline_p=base.result.p_value if base.result else float("nan"),
        universes=len(snapshot.garden.universes),
        seconds=round(time.monotonic() - started, 2),
    )
