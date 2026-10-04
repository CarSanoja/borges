from __future__ import annotations

import re

from borges.analysis.models import AnalysisPlan
from borges.garden.models import EstimandChange, Garden, Universe
from borges.garden.noop import single_universe


def design_terms(universe: Universe) -> set[str] | None:
    for trace in universe.traces:
        design = trace.design
        if design and isinstance(design.get("terms"), list):
            return {str(term) for term in design["terms"]}
    return None


UNNAMED = re.compile(r"x\d+")


def estimand_detail(baseline: Universe, universe: Universe) -> str | None:
    before, after = design_terms(baseline), design_terms(universe)
    if before is None or after is None or before == after:
        return None
    if any(UNNAMED.fullmatch(t) for t in before | after):
        if len(before) == len(after):
            return None
        return (
            f"changes the number of covariates of the model from {len(before)} to "
            f"{len(after)}: adjusted versus unadjusted answers a different question, so this "
            "is an estimand change, not a re-analysis of the same quantity"
        )
    added, removed = sorted(after - before), sorted(before - after)
    parts = []
    if added:
        parts.append("adds " + ", ".join(added))
    if removed:
        parts.append("removes " + ", ".join(removed))
    return (
        "changes the covariates of the model (" + "; ".join(parts) + "): adjusted versus "
        "unadjusted answers a different question, so this is an estimand change, not a "
        "re-analysis of the same quantity"
    )


def estimand_changes(plan: AnalysisPlan, garden: Garden) -> list[EstimandChange]:
    baseline = garden.baseline
    if baseline is None:
        return []
    found: list[EstimandChange] = []
    for step in plan.decision_steps:
        for option in step.options:
            if option.id == step.default.id:
                continue
            single = single_universe(garden, step.id, option.id)
            detail = estimand_detail(baseline, single) if single is not None else None
            if detail is not None:
                found.append(
                    EstimandChange(
                        step_id=step.id, option_id=option.id, label=option.label, detail=detail
                    )
                )
    return found
