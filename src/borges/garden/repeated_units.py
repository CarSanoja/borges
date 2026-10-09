from __future__ import annotations

from borges.analysis.models import AnalysisPlan, RepeatedUnit
from borges.garden.models import Garden, Universe


def _clustered(universe: Universe) -> bool:
    return any(
        str((trace.design or {}).get("cov_type") or "").lower() == "cluster"
        for trace in universe.traces
    )


def fitted_unit(plan: AnalysisPlan, garden: Garden) -> RepeatedUnit | None:
    """The repeated unit the original model fits one row of, when its n is that unit's count.

    An A/B run (r_20261009T025034_64dcc8) kept one row per user after summing the sessions, so
    it fitted 15,000 rows for 15,000 users out of 21,624 sessions; the report still said the rows
    repeat user_id and that the model dropped the rows with missing values."""
    baseline = garden.baseline
    if baseline is None or baseline.result is None:
        return None
    n = baseline.result.n
    return next((u for u in plan.dataset.repeated_units if u.n_units == n), None)


def repeated_unit_caveats(plan: AnalysisPlan, garden: Garden) -> list[str]:
    """One caveat per repeated unit when the original analysis does not cluster its errors."""
    baseline = garden.baseline
    if baseline is None or baseline.status != "done" or _clustered(baseline):
        return []
    if fitted_unit(plan, garden) is not None:
        return []
    return [
        f"rows repeat {unit.n_units:,} {unit.name} values; errors not clustered by "
        f"{unit.name} may be too narrow"
        for unit in plan.dataset.repeated_units
    ]
