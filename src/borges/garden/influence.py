from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.garden.models import DecisionInfluence, Flip, Garden, Report


def decision_influence(plan: AnalysisPlan, garden: Garden) -> list[DecisionInfluence]:
    raise NotImplementedError


def robustness(garden: Garden) -> float:
    raise NotImplementedError


def build_report(plan: AnalysisPlan, garden: Garden, flip: Flip | None) -> Report:
    raise NotImplementedError
