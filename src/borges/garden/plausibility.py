from __future__ import annotations

import math

from borges.analysis.models import AnalysisResult

IMPLAUSIBLE_REASON = "implausible estimate"
WIDTH_FACTOR = 1000.0
SCALE_FACTOR = 100.0


def is_implausible(baseline: AnalysisResult, result: AnalysisResult) -> bool:
    if not math.isfinite(result.estimate):
        return True
    half_width = (baseline.ci_high - baseline.ci_low) / 2
    scale = max(abs(baseline.estimate), half_width)
    far_from_baseline = abs(result.estimate - baseline.estimate) > WIDTH_FACTOR * half_width
    return far_from_baseline and abs(result.estimate) > SCALE_FACTOR * scale


def implausible_message(baseline: AnalysisResult, result: AnalysisResult) -> str:
    return (
        f"{IMPLAUSIBLE_REASON}: {result.estimate:.6g} is far outside the scale of the baseline "
        f"({baseline.estimate:.6g} with a 95% CI from {baseline.ci_low:.6g} to "
        f"{baseline.ci_high:.6g}); the implementation is probably wrong"
    )
