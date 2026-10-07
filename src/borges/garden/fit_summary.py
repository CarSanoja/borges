"""What a model step fitted: the keys of its rows and the mean of each design column."""

from __future__ import annotations

from borges.analysis.models import StepTrace


def fit_summary(traces: list[StepTrace]) -> dict[str, object]:
    design = next((t.design for t in reversed(traces) if t.design), None) or {}
    return {
        key: design[key] for key in ("row_keys", "means", "names") if design.get(key) is not None
    }
