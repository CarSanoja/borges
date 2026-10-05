"""Quantile regressions of an outcome with few distinct values.

At 0b92e6c the marp_religiosity minimal flip fitted a median regression to the mean of the two
general well-being items, an outcome with 9 distinct values and a third of its 10,503 rows at one
of them. The conditional median of such an outcome moves in steps, so the fitted slope was 7.3e-07
and the verdict NO CLEAR EVIDENCE: a property of the outcome's coarseness, not evidence that the
association is absent. The same model gave 0.066 on the overall well-being mean (122 values).
Quantiles of a discrete outcome are usually fitted after jittering it (Machado and Santos Silva,
2005).
"""

from __future__ import annotations

from borges.garden.models import Garden, Universe

MAX_LEVELS = 20
QUANTILE_MODELS = frozenset({"QuantReg"})


def _levels(universe: Universe) -> int | None:
    for trace in universe.traces:
        design = trace.design
        if design and design.get("model") in QUANTILE_MODELS:
            levels = design.get("endog_levels")
            return int(levels) if isinstance(levels, int) else None
    return None


def coarse_quantile_universes(garden: Garden) -> list[tuple[Universe, int]]:
    found = []
    for universe in garden.universes.values():
        if universe.status != "done" or universe.result is None:
            continue
        levels = _levels(universe)
        if levels is not None and levels <= MAX_LEVELS:
            found.append((universe, levels))
    return found


def discrete_quantile_caveats(garden: Garden, flip_universe_id: str | None) -> list[str]:
    found = coarse_quantile_universes(garden)
    if not found:
        return []
    levels = sorted({k for _, k in found})
    span = f"{levels[0]}" if len(levels) == 1 else f"{levels[0]} to {levels[-1]}"
    smallest = min(abs(u.result.estimate) for u, _ in found if u.result is not None)
    count = len(found)
    head = "1 universe fits" if count == 1 else f"{count} universes fit"
    flip = ""
    if any(u.id == flip_universe_id for u, _ in found):
        flip = "; it is the minimal flip" if count == 1 else "; the minimal flip is one of them"
    return [
        f"{head} a quantile regression to an outcome with only {span} distinct values{flip}. "
        "The conditional quantile of such an outcome moves in steps, so its slope is often "
        f"exactly zero (the smallest estimate here is {smallest:.2g}): these verdicts reflect how "
        "coarse the outcome is, not the association. Quantiles of a discrete outcome are usually "
        "fitted after jittering it."
    ]
