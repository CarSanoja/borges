from __future__ import annotations

import math

from borges.analysis.models import AnalysisResult

RELATIVE_WIDTH_FLOOR = 1e-6
ABSOLUTE_WIDTH_FLOOR = 1e-9


def interval_error(result: AnalysisResult) -> str | None:
    values = {
        "estimate": result.estimate,
        "ci_low": result.ci_low,
        "ci_high": result.ci_high,
    }
    bad = [name for name, value in values.items() if not math.isfinite(value)]
    if bad:
        return f"non-finite {', '.join(bad)}: the standard error behind the interval is not finite"
    low, high, est = result.ci_low, result.ci_high, result.estimate
    span = f"the 95% interval [{low:.6g}, {high:.6g}]"
    if low > high:
        return f"{span} is inverted: ci_low must be smaller than ci_high"
    width = high - low
    floor = max(RELATIVE_WIDTH_FLOOR * abs(est), ABSOLUTE_WIDTH_FLOOR)
    if width <= floor:
        return (
            f"{span} has zero width relative to the estimate {est:.6g}: the standard error "
            f"is degenerate, so the interval carries no uncertainty"
        )
    tol = 1e-6 * max(1.0, abs(low), abs(high))
    if not low - tol <= est <= high + tol:
        return f"{span} does not contain the estimate {est:.6g}"
    return None
