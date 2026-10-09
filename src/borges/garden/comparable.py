"""Universes whose estimate is on another scale than the original one.

A randhie garden put a zero-inflated Poisson's raw log-link coefficient (-0.0315) in one range with
Poisson options reporting an average marginal effect (-0.188) and OLS slopes in outcome units
(r_20261009T003245_1d5875); the range, the largest shift and the robustness share compared them.
Such universes stay listed, labelled, and are left out of every comparison of estimates.
"""

from __future__ import annotations

from borges.garden.estimand import scale_detail
from borges.garden.models import Garden, Universe


def other_scale(baseline: Universe | None, universe: Universe) -> str | None:
    if baseline is None or universe.kind == "baseline" or universe.result is None:
        return None
    return scale_detail(baseline, universe)


def comparable(baseline: Universe | None, universe: Universe) -> bool:
    return other_scale(baseline, universe) is None


def scale_caveats(garden: Garden) -> list[str]:
    baseline = garden.baseline
    apart = [
        u for u in garden.finished() if u.kind != "verification" and not comparable(baseline, u)
    ]
    if not apart:
        return []
    low = min(u.result.estimate for u in apart if u.result)
    high = max(u.result.estimate for u in apart if u.result)
    return [
        f"{len(apart)} universes report an estimate on another scale than the original one "
        f"(from {low:.3g} to {high:.3g}): they are not comparable with it, so they are left out of "
        "the range of estimates, the largest shift and the robustness share."
    ]
