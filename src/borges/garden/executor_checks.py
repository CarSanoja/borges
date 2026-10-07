from __future__ import annotations

from borges.analysis.models import AnalysisPlan, AnalysisResult
from borges.garden.degenerate import degenerate_message, is_degenerate
from borges.garden.mirror import is_mirror, mirror_message
from borges.garden.models import UniverseKind
from borges.garden.plausibility import implausible_message, is_implausible
from borges.garden.reversal import find_reversal
from borges.sandbox.backend import BranchBackend


async def screen_result(
    backend: BranchBackend,
    plan: AnalysisPlan,
    root_id: str,
    kind: UniverseKind,
    baseline_result: AnalysisResult | None,
    baseline_checkpoints: list[str],
    checkpoints: list[str],
    choices: dict[str, str],
    result: AnalysisResult,
) -> str | None:
    if kind == "baseline":
        return None
    if baseline_result is not None and is_implausible(baseline_result, result):
        return implausible_message(baseline_result, result)
    if baseline_result is not None and is_degenerate(baseline_result, result):
        return degenerate_message(baseline_result, result)
    if baseline_result is not None and is_mirror(
        baseline_result, result, plan.decision_rule.threshold
    ):
        return mirror_message(baseline_result, result)
    if baseline_checkpoints:
        return await find_reversal(
            backend, plan, root_id, baseline_checkpoints, checkpoints, choices
        )
    return None
