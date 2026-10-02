from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.garden.executor import GardenExecutor
from borges.runtime.alias_backend import AliasBackend
from borges.runtime.baseline_restore import ResumeError, restore_baseline
from borges.runtime.universe_checkpoint import RestoredUniverses, apply_options


async def restore_search(
    executor: GardenExecutor,
    backend: AliasBackend,
    plan: AnalysisPlan,
    restored: RestoredUniverses,
) -> None:
    baseline = restored.baseline()
    if baseline is None:
        raise ResumeError("no baseline checkpoint to resume from")
    await restore_baseline(executor, backend, plan, baseline)
    for universe_id in restored.order:
        apply_options(plan, restored.payloads[universe_id])
