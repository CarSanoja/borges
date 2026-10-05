from __future__ import annotations

import re

from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.models import DecisionRule

STANDARDISED = re.compile(r"\bstandardi[sz]ed\b", re.IGNORECASE)
MEAN_DIFFERENCE = re.compile(r"\bmean difference\b|\bcohen", re.IGNORECASE)


def reads_standardised(metric: str) -> bool:
    return STANDARDISED.search(metric) is not None


def _missing(spec: ModelSpecOutput, rule: DecisionRule | None) -> list[str]:
    if rule is None or spec.family != "ols" or not STANDARDISED.search(rule.metric):
        return []
    wanted = [spec.outcome]
    if spec.exposure_level is None and not MEAN_DIFFERENCE.search(rule.metric):
        wanted += [spec.exposure, spec.moderator]
    return [c for c in wanted if c is not None and c not in spec.standardize]


def standardize_for_rule(spec: ModelSpecOutput, rule: DecisionRule | None) -> ModelSpecOutput:
    """A marp_norms spec at 508fe2e z-scored the predictors but not the outcome; its retry gave
    up and the free code written instead left out the interaction's main effects."""
    missing = _missing(spec, rule) if spec.supported else []
    if not missing:
        return spec
    return spec.model_copy(update={"standardize": [*spec.standardize, *missing]})


def standardized_problems(spec: ModelSpecOutput, rule: DecisionRule | None) -> list[str]:
    missing = _missing(spec, rule)
    if not missing:
        return []
    return [
        "the decision rule reports a standardised coefficient, which z-scores the outcome as "
        f"well as the predictors; add {', '.join(repr(c) for c in missing)} to standardize"
    ]
