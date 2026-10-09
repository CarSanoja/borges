from __future__ import annotations

import math
from statistics import NormalDist

from borges.analysis.models import AnalysisResult

RELATIVE_WIDTH_FLOOR = 1e-6
ABSOLUTE_WIDTH_FLOOR = 1e-9
Z95 = NormalDist().inv_cdf(0.975)
Z_CAP = 8.0


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
    return p_value_error(result)


def _z_of_p(p: float) -> float:
    if p < 1e-15:
        return Z_CAP
    return min(NormalDist().inv_cdf(1 - min(p, 1.0) / 2), Z_CAP) if p < 1 else 0.0


def _z_from_interval(est: float, low: float, high: float, null: float) -> float | None:
    half = est - low if null < est else high - est
    return min(abs(est - null) / (half / Z95), Z_CAP) if half > 0 else None


def _agree(reported: float, implied: float) -> bool:
    close = abs(reported - implied) <= max(1.0, 0.5 * max(reported, implied))
    return close or min(reported, implied) >= Z95


def p_value_error(result: AnalysisResult) -> str | None:
    """The p-value has to be one the interval could give: against 0, against 1, or against 1 on
    the log scale of a ratio, using the interval's half-width on the null's side. A residual
    bootstrap centred its draws on the fitted coefficient, so every p-value came out as 1.0 beside
    an interval that put it near 0.13, and those universes counted as agreeing (9 October). Two
    figures that both clear 5% are not a disagreement that can move a verdict. Over 10,470
    recorded results the check flags only those three."""
    est, low, high = result.estimate, result.ci_low, result.ci_high
    candidates = [_z_from_interval(est, low, high, 0.0), _z_from_interval(est, low, high, 1.0)]
    if low > 0 and est > 0:
        candidates.append(_z_from_interval(math.log(est), math.log(low), math.log(high), 0.0))
    implied = [z for z in candidates if z is not None]
    reported = _z_of_p(result.p_value)
    if not implied or any(_agree(reported, z) for z in implied):
        return None
    return (
        f"the p-value {result.p_value:.3g} is not one the 95% interval [{low:.6g}, {high:.6g}] "
        f"around {est:.6g} could give: the p-value and the interval come from different tests"
    )
