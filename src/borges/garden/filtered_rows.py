"""Rows the data steps of the original analysis drop before its model.

An audit run (r_20261009T084632_39cf88) asked whether more review hours lower restatements; its
filter "Exclude extreme revenue and missing hours" kept 1,303 of 1,500 engagements, and the hours
were missing mostly for the most complex clients. Nothing in the report said that 13 % of the
engagements were not analysed. When the data steps of the original analysis keep less than
KEPT_SHARE of the uploaded rows, the report names each step that dropped rows and how many.
"""

from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Garden

KEPT_SHARE = 0.95


def filtered_rows_caveats(plan: AnalysisPlan, garden: Garden) -> list[str]:
    baseline = garden.baseline
    total = plan.dataset.n_rows
    if baseline is None or baseline.result is None or len(baseline.traces) < 2 or total <= 0:
        return []
    reach = baseline.traces[-1].rows_before
    if reach >= KEPT_SHARE * total:
        return []
    titles = {s.id: s.title for s in plan.steps}
    drops = [
        f"'{titles.get(t.step_id, t.step_id)}' drops {t.rows_before - t.rows_after:,}"
        for t in baseline.traces[:-1]
        if t.rows_after < t.rows_before
    ]
    if not drops:
        return []
    return [
        f"The original analysis's model receives {reach:,} of the {total:,} uploaded rows "
        f"({1 - reach / total:.0%} left out): {'; '.join(drops)}. The verdict describes the rows "
        "kept; if the dropped rows differ from them, as rows with missing values often do, it "
        "may not hold for every row."
    ]
