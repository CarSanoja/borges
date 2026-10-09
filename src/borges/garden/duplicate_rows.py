from __future__ import annotations

from borges.analysis.models import AnalysisPlan

MIN_DUPLICATE_SHARE = 0.03


def duplicate_row_caveats(plan: AnalysisPlan) -> list[str]:
    """A plain caveat when a few percent or more of the rows are exact copies of another row."""
    dataset = plan.dataset
    if dataset.n_rows <= 0 or dataset.duplicate_rows / dataset.n_rows < MIN_DUPLICATE_SHARE:
        return []
    return [
        f"{dataset.duplicate_rows:,} of {dataset.n_rows:,} rows are exact copies of another "
        "row; if they are repeated records of the same observation rather than genuine "
        "repeats, the effective sample is smaller than it looks and the intervals are too narrow"
    ]
