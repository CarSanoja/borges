from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Change, Flip, Garden


def changes_for(plan: AnalysisPlan, choices: dict[str, str]) -> list[Change]:
    raise NotImplementedError


def single_flip_choices(plan: AnalysisPlan) -> list[dict[str, str]]:
    raise NotImplementedError


def pair_flip_choices(plan: AnalysisPlan, garden: Garden, limit: int) -> list[dict[str, str]]:
    raise NotImplementedError


def minimal_flip(plan: AnalysisPlan, garden: Garden) -> Flip | None:
    raise NotImplementedError
