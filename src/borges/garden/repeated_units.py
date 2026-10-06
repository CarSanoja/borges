from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Garden, Universe


def _clustered(universe: Universe) -> bool:
    return any(
        str((trace.design or {}).get("cov_type") or "").lower() == "cluster"
        for trace in universe.traces
    )


def repeated_unit_caveats(plan: AnalysisPlan, garden: Garden) -> list[str]:
    """One caveat per repeated unit when the original analysis does not cluster its errors."""
    baseline = garden.baseline
    if baseline is None or baseline.status != "done" or _clustered(baseline):
        return []
    return [
        f"rows repeat {unit.n_units:,} {unit.name} values; errors not clustered by "
        f"{unit.name} may be too narrow"
        for unit in plan.dataset.repeated_units
    ]
