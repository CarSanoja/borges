from __future__ import annotations

import os
import re

from borges.analysis.models import AnalysisPlan
from borges.garden.measure import measure_detail
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
MIN_STEM = 4


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


def _renamed(added: list[str], removed: list[str], columns: set[str]) -> bool:
    """One derived variable named differently by two options, not a change of covariates."""
    if len(added) != 1 or len(removed) != 1 or {*added, *removed} & columns:
        return False
    return len(os.path.commonprefix([added[0].lower(), removed[0].lower()])) >= MIN_STEM


def reported_term(universe: Universe) -> tuple[str, object] | None:
    for trace in universe.traces:
        if trace.design and isinstance(trace.design.get("exposure"), str):
            return str(trace.design["exposure"]), trace.design.get("exposure_binary")
    return None


def exposure_detail(baseline: Universe, universe: Universe, columns: set[str] | None) -> str | None:
    """Another quantity's coefficient reported as the estimate: two dataset columns (contact and
    campaign, bank, 2a2d925), or a 0/1 cut and the scale it cuts (dark and skin_tone, red_cards,
    b4e2f4e). Two names for one 0/1 indicator are the same exposure."""
    before, after = reported_term(baseline), reported_term(universe)
    if before is None or after is None or before[0] == after[0]:
        return None
    raw = columns is not None and {before[0], after[0]} <= columns
    if not raw and before[1] == after[1]:
        return None
    return (
        f"reports the coefficient of {after[0]} where the original analysis reports "
        f"{before[0]}: another exposure answers another question, so this is an estimand "
        "change, not a re-analysis of the same quantity"
    )


def _outcome(universe: Universe) -> str | None:
    for trace in universe.traces:
        if trace.design and isinstance(trace.design.get("outcome"), str):
            return str(trace.design["outcome"])
    return None


def outcome_detail(baseline: Universe, universe: Universe, columns: set[str] | None) -> str | None:
    """Another column of the data modelled as the outcome: a marp_norms flip replaced overall
    well-being with its social subscale and was reported as a re-analysis (597c38e)."""
    before, after = _outcome(baseline), _outcome(universe)
    if before is None or after is None or before == after or columns is None:
        return None
    if not {before, after} <= columns:
        return None
    return (
        f"models another outcome ({after} instead of {before}): another outcome answers "
        "another question, so this is an estimand change, not a re-analysis of the same quantity"
    )


def _covariate_terms(universe: Universe) -> set[str] | None:
    terms, exposure = design_terms(universe), reported_term(universe)
    if terms is None or exposure is None:
        return terms
    return terms - {exposure[0]}


def design_width(universe: Universe) -> int | None:
    for trace in universe.traces:
        if trace.design and isinstance(trace.design.get("columns"), int):
            return int(trace.design["columns"])
    return None


def _count_detail(baseline: Universe, universe: Universe, before: int, after: int) -> str | None:
    """Unnamed terms (a model fitted on numpy arrays) cannot be matched to covariates by name.

    Named dummies collapse into the column they encode and unnamed ones cannot, so counting terms
    told a marp_religiosity quantile regression at 0b92e6c, fitted on the same seven design
    columns as the OLS baseline, apart as a change from 5 to 6 covariates and its flip as an
    estimand change. When both designs report their width, the widths are compared.
    """
    widths = design_width(baseline), design_width(universe)
    what = "covariates"
    if None not in widths:
        before, after = widths[0] or 0, widths[1] or 0
        what = "columns"
    if before == after:
        return None
    return (
        f"changes the number of {what} of the model from {before} to {after}: adjusted versus "
        "unadjusted answers a different question, so this is an estimand change, not a "
        "re-analysis of the same quantity"
    )


def estimand_detail(
    baseline: Universe, universe: Universe, columns: set[str] | None = None
) -> str | None:
    scale = (
        scale_detail(baseline, universe)
        or outcome_detail(baseline, universe, columns)
        or exposure_detail(baseline, universe, columns)
        or measure_detail(baseline, universe)
    )
    if scale is not None:
        return scale
    before, after = design_terms(baseline), design_terms(universe)
    if reported_term(baseline) is not None and reported_term(universe) is not None:
        before, after = _covariate_terms(baseline), _covariate_terms(universe)
    if before is None or after is None or before == after:
        return None
    if any(UNNAMED.fullmatch(t) for t in before | after):
        return _count_detail(baseline, universe, len(before), len(after))
    added, removed = sorted(after - before), sorted(before - after)
    if columns is not None and _renamed(added, removed, columns):
        return None
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
    columns = {c.name for c in plan.dataset.columns}
    found: list[EstimandChange] = []
    for step in plan.decision_steps:
        for option in step.options:
            if option.id == step.default.id:
                continue
            single = single_universe(garden, step.id, option.id)
            detail = estimand_detail(baseline, single, columns) if single is not None else None
            if detail is not None:
                found.append(
                    EstimandChange(
                        step_id=step.id, option_id=option.id, label=option.label, detail=detail
                    )
                )
    return found
