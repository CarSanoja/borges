from __future__ import annotations

import hashlib
from typing import Any

from borges.analysis import harness
from borges.analysis.models import AnalysisPlan
from borges.garden.executor import GardenExecutor
from borges.garden.models import Universe
from borges.garden.prefix_cache import Prefix, PrefixNode
from borges.runtime.alias_backend import AliasBackend
from borges.runtime.universe_checkpoint import apply_options
from borges.sandbox.backend import Checkpoint


class ResumeError(RuntimeError):
    pass


async def restore_baseline(
    executor: GardenExecutor,
    backend: AliasBackend,
    plan: AnalysisPlan,
    payload: dict[str, Any],
) -> Universe:
    """Rebuild the baseline's sandbox state silently and keep its recorded checkpoint ids."""
    baseline = Universe.model_validate(payload["universe"])
    old_root = payload.get("root_id")
    if not old_root:
        raise ResumeError("the baseline checkpoint has no root checkpoint")
    apply_options(plan, payload)
    real_root = await backend.root({harness.DATA_FILE: executor.data})
    backend.aliases[old_root] = real_root
    executor.root = Checkpoint(old_root, None, backend.name)
    emit, executor.emit = executor.emit, None
    parent, old_parent = real_root, executor.root
    prefix: Prefix = ()
    try:
        for index, step in enumerate(plan.steps):
            option = step.option(baseline.choices[step.id])
            digest = hashlib.sha1((option.code or "").encode()).hexdigest()[:12]
            prefix = (*prefix, (step.id, option.id, digest))
            node = await executor._compute_prefix(parent, index, step.id, option.id)
            if not node.ok or node.checkpoint is None:
                raise ResumeError(f"the baseline could not be rebuilt: {node.error}")
            old_id = baseline.checkpoints[index]
            backend.aliases[old_id] = node.checkpoint
            recorded = Checkpoint(old_id, old_parent.id, backend.name)
            executor._cache.seed(prefix, PrefixNode(recorded, node.traces, node.result))
            parent, old_parent = node.checkpoint, recorded
    finally:
        executor.emit = emit
    executor.baseline_verdict = baseline.verdict
    executor.baseline_result = baseline.result
    executor.baseline_checkpoints = list(baseline.checkpoints)
    return baseline
