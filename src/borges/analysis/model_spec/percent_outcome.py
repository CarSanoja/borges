"""An outcome written as a column times 100 under a rule in percentage points.

A checkout model option at 0280150 said "Use outcome = converted * 100 to express the effect in
percentage points". The translated spec named that expression as its outcome, the template was
skipped because no column has that name, and the free code written instead fitted the scaled
outcome, returned percentage points and failed the unit check on every repair: the default model
was lost. Borges converts a difference in proportions to percentage points itself, so under such a
rule the outcome is the column.
"""

from __future__ import annotations

import re

from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.models import DecisionRule
from borges.analysis.result_scale import detect_scale

TIMES_100 = re.compile(
    r"^\s*\(?\s*([A-Za-z_]\w*)\s*\)?\s*\*\s*100(?:\.0*)?\s*$"
    r"|^\s*100(?:\.0*)?\s*\*\s*\(?\s*([A-Za-z_]\w*)\s*\)?\s*$"
)


def percent_outcome(
    spec: ModelSpecOutput, rule: DecisionRule | None, available: list[str]
) -> ModelSpecOutput:
    if rule is None or spec.outcome is None or detect_scale(rule.metric) == 1.0:
        return spec
    match = TIMES_100.match(spec.outcome)
    column = (match.group(1) or match.group(2)) if match else None
    if column is None or column not in available:
        return spec
    return spec.model_copy(update={"outcome": column})
