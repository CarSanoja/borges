"""A result that is the starting point with one variable's coding reversed.

fertility_vote on 7 October, runs 28 and 29: the model options "low fertility, committed and their
product" and "interaction = low_fert * committed" gave +1.5901 and +1.6229 against the starting
point's -1.5901 and -1.6230, on the same rows with the same p-value, and each was reported as the
smallest flip. Coding the other group as 1 changes the sign of the coefficient and nothing else:
it is the same analysis. The reversal check compares the columns transform and feature steps
build and cannot see a coding inside the model step, so the result itself is compared with the
starting point's: same n, the estimate mirrored about the null of the decision rule, the same
interval width and the same p-value.
"""

from __future__ import annotations

import math

from borges.analysis.models import AnalysisResult

MIRROR_REASON = "same analysis, reversed coding"
REL_TOL = 1e-3


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=1e-9)


def is_mirror(baseline: AnalysisResult, result: AnalysisResult, null: float) -> bool:
    if result.n != baseline.n or not _close(result.p_value, baseline.p_value):
        return False
    if null == 0.0:
        width, base_width = result.ci_high - result.ci_low, baseline.ci_high - baseline.ci_low
        mirrored = _close(result.estimate, -baseline.estimate)
        return mirrored and _close(width, base_width) and baseline.estimate != 0
    if null == 1.0 and min(result.estimate, baseline.estimate, result.ci_low, baseline.ci_low) > 0:
        mirrored = _close(result.estimate * baseline.estimate, 1.0)
        ratio, base_ratio = result.ci_high / result.ci_low, baseline.ci_high / baseline.ci_low
        return mirrored and _close(ratio, base_ratio) and not _close(baseline.estimate, 1.0)
    return False


def mirror_message(baseline: AnalysisResult, result: AnalysisResult) -> str:
    return (
        f"{MIRROR_REASON}: {result.estimate:+.4f} on the same {result.n} rows with the same "
        f"p-value as the starting point's {baseline.estimate:+.4f}, so the option codes the other "
        "group as 1 and is the same analysis, not a different one"
    )
