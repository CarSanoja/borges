from __future__ import annotations

import shlex

from borges.analysis import harness
from borges.analysis.models import AnalysisPlan, AnalysisResult
from borges.garden.executor import STEP_TIMEOUT_S, GardenExecutor
from borges.garden.models import Flip, Garden
from borges.sandbox.backend import BranchBackend

TOLERANCE = 1e-9


def _same(rerun: AnalysisResult | None, expected: AnalysisResult) -> bool:
    return (
        rerun is not None
        and abs(rerun.estimate - expected.estimate) <= TOLERANCE
        and abs(rerun.p_value - expected.p_value) <= TOLERANCE
        and abs(rerun.ci_low - expected.ci_low) <= TOLERANCE
        and abs(rerun.ci_high - expected.ci_high) <= TOLERANCE
        and rerun.n == expected.n
    )


async def verify_flip(
    backend: BranchBackend,
    plan: AnalysisPlan,
    data: bytes,
    flip: Flip,
    garden: Garden,
    step_timeout_s: float = STEP_TIMEOUT_S,
) -> Flip:
    original = garden.universes[flip.universe_id]
    executor = GardenExecutor(
        backend, plan, data, emit=None, reuse_prefixes=False, step_timeout_s=step_timeout_s
    )
    await executor.setup()
    baseline_rerun = await executor.run_universe(plan.default_choices(), "baseline")
    rerun = await executor.run_universe(original.choices, "verification")
    reproduced = (
        _same(baseline_rerun.result, flip.baseline_result)
        and _same(rerun.result, flip.flipped_result)
        and baseline_rerun.verdict == flip.baseline_verdict
        and rerun.verdict == flip.flipped_verdict
        and flip.baseline_verdict != flip.flipped_verdict
    )
    commands = [
        shlex.join(harness.step_command(step.id, original.choices[step.id])) for step in plan.steps
    ]
    return flip.model_copy(
        update={
            "reproduced": reproduced,
            "reproduce_command": " && ".join(commands),
        }
    )
