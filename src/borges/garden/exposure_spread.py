"""An estimate is per unit of the exposure, so options that build the exposure on another scale
move the estimate without changing what it says: in marp_religiosity (2327203) the first
principal component of nine items had about three times the spread of their mean, the slope fell
from 0.093 to 0.045, and the report called that the influence of the scale choice."""

from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Garden, Universe

SPREAD_RATIO = 1.5
SAME_SCALE = 1.1


def exposure_sd(universe: Universe) -> float | None:
    for trace in universe.traces:
        design = trace.design or {}
        sd = design.get("exposure_sd")
        if isinstance(sd, int | float) and sd > 0 and not design.get("exposure_binary"):
            return float(sd)
    return None


def _ratio(values: list[float]) -> float:
    return max(values) / min(values)


def _scale_step(plan: AnalysisPlan, sds: dict[str, float], garden: Garden) -> str | None:
    for step in plan.decision_steps:
        by_option: dict[str, list[float]] = {}
        rows: dict[str, set[int]] = {}
        for universe in garden.finished():
            if universe.id in sds and universe.result is not None:
                option = universe.choices[step.id]
                by_option.setdefault(option, []).append(sds[universe.id])
                rows.setdefault(option, set()).add(universe.result.n)
        if len(by_option) < 2 or any(_ratio(v) > SAME_SCALE for v in by_option.values()):
            continue
        if len({frozenset(n) for n in rows.values()}) > 1:
            continue
        means = {o: sum(v) / len(v) for o, v in by_option.items()}
        if _ratio(list(means.values())) < SPREAD_RATIO:
            continue
        labels = {o.id: o.label for o in step.options}
        spread = ", ".join(f"{means[o]:.3g} with '{labels.get(o, o)}'" for o in sorted(means))
        return (
            f"The options of '{step.title}' build the exposure on different scales (standard "
            f"deviation {spread}): an estimate is per unit of the exposure, so estimates, ranges "
            "and influences across these options differ partly by scale; compare their verdicts, "
            "not their sizes."
        )
    return None


def exposure_spread_notes(plan: AnalysisPlan, garden: Garden) -> list[str]:
    sds = {u.id: sd for u in garden.finished() if (sd := exposure_sd(u)) is not None}
    if len(sds) < 2 or _ratio(list(sds.values())) < SPREAD_RATIO:
        return []
    named = _scale_step(plan, sds, garden)
    return [named] if named is not None else []
