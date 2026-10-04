from __future__ import annotations

import math
import re
from typing import Any

from borges.garden.models import Garden, Universe

LOG_WORDS = re.compile(r"\blog|logarithm", re.IGNORECASE)


def log_outcome(universe: Universe) -> dict[str, Any] | None:
    for trace in universe.traces:
        scale = (trace.design or {}).get("outcome_log")
        if isinstance(scale, dict) and scale.get("column"):
            return scale
    return None


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
