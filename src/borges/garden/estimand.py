from __future__ import annotations

import re

from borges.analysis.models import AnalysisPlan
from borges.garden.models import EstimandChange, Garden, Universe
from borges.garden.noop import single_universe
from borges.garden.outcome_scale import log_outcome


def design_terms(universe: Universe) -> set[str] | None:
    for trace in universe.traces:
        design = trace.design
        if design and isinstance(design.get("terms"), list):
            return {str(term) for term in design["terms"]}
    return None


UNNAMED = re.compile(r"x\d+")


def _scale_name(scale: dict[str, object] | None, column: str) -> str:
    if scale is None:
        return column
    kind = scale.get("kind")
    return f"a log-link model of {column}" if kind == "log link" else f"{kind}({column})"


def scale_detail(baseline: Universe, universe: Universe) -> str | None:
    before, after = log_outcome(baseline), log_outcome(universe)
    if before is None and after is None:
        return None
    if before is not None and after is not None and before.get("kind") == after.get("kind"):
        return None
    column = str((before or after or {}).get("column") or "the outcome")
    return (
        f"puts the outcome on another scale ({_scale_name(after, column)} instead of "
        f"{_scale_name(before, column)}): its estimate is not comparable with the original one, "
        "so this is an estimand change, not a re-analysis of the same quantity"
    )


def estimand_detail(baseline: Universe, universe: Universe) -> str | None:
    scale = scale_detail(baseline, universe)
    if scale is not None:
        return scale
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
