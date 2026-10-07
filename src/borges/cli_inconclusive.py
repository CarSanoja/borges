from __future__ import annotations

from borges.analysis.models import AnalysisResult, DecisionRule
from borges.garden.models import Garden
from borges.runs.models import RunSnapshot


def is_inconclusive(verdict: str, result: AnalysisResult, rule: DecisionRule | None) -> bool:
    if rule is None:
        return False
    return verdict == rule.negative_label and result.p_value >= rule.alpha


def smallest_p(garden: Garden) -> float | None:
    values = [
        universe.result.p_value
        for universe in garden.universes.values()
        if universe.status == "done"
        and universe.kind != "verification"
        and universe.result is not None
    ]
    return min(values) if values else None


def snapshot_rule(snapshot: RunSnapshot) -> DecisionRule | None:
    if snapshot.decision_rule is not None:
        return snapshot.decision_rule
    return snapshot.plan.decision_rule if snapshot.plan is not None else None


def inconclusive_clause(min_p: float | None, alpha: float, agree: int, total: int) -> str:
    head = f"{agree} of {total} paths are also inconclusive"
    if min_p is None:
        return head
    if min_p < alpha:
        return f"{head}; smallest p-value {min_p:.4g}"
    return f"{head}: no path reached p < {alpha:g}; smallest p-value {min_p:.4g}"
