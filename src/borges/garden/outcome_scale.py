from __future__ import annotations

import math
import re
from typing import Any

from borges.analysis.harness_outcome import ZERO_INFLATED_MODELS
from borges.garden.models import Garden, Universe

CHANGE = r"(?:more|less|fewer|higher|lower|increase|decrease|change|rise|drop)"
LOG_WORDS = re.compile(
    rf"\blog(?!it|istic|ic)|logarithm|(?:%|\bpercent(?:age)?)\s*(?:point\s+)?{CHANGE}",
    re.IGNORECASE,
)


def _zero_inflated(universe: Universe) -> dict[str, Any] | None:
    """A trace recorded before the harness read zero-inflated models: a count model that keeps no
    separate coefficient beside its estimate reports the raw log-link coefficient."""
    if universe.result is None or "coefficient" in universe.result.extra:
        return None
    for trace in reversed(universe.traces):
        design = trace.design or {}
        if design.get("model") in ZERO_INFLATED_MODELS:
            return {"kind": "log link", "column": str(design.get("outcome") or "the outcome")}
    return None


def log_outcome(universe: Universe) -> dict[str, Any] | None:
    for trace in universe.traces:
        scale = (trace.design or {}).get("outcome_log")
        if isinstance(scale, dict) and scale.get("column"):
            return scale
    return _zero_inflated(universe)


def scale_note(garden: Garden) -> str | None:
    """A sentence on the log scale of the original estimate, or None when it is on the metric."""
    baseline = garden.baseline
    if baseline is None or baseline.result is None:
        return None
    scale = log_outcome(baseline)
    if scale is None:
        return None
    estimate = baseline.result.estimate
    change = 100 * (math.exp(estimate) - 1)
    column, kind = scale["column"], scale["kind"]
    model = (
        f"a log-link model of {column}" if kind == "log link" else f"a model of {kind}({column})"
    )
    return (
        f"The original analysis is {model}, so its estimate {estimate:.3g} is on the log scale: "
        f"about {abs(change):.1f}% {'more' if change >= 0 else 'less'} {column} per unit of the "
        f"exposure, not {estimate:.3g} additional {column}."
    )


def mentions_log_scale(text: str) -> bool:
    return LOG_WORDS.search(text) is not None
