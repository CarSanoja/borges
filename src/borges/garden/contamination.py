from __future__ import annotations

import re

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Change, Garden
from borges.garden.noop import single_universe, trace_of

INVALID_ROWS = re.compile(
    r"\b(internal|test|tests|testing|bot|bots|duplicate|duplicates|duplicated|ineligible|"
    r"invalid|staff|employee|employees|qa|spam|fraud|fraudulent)\b",
    re.IGNORECASE,
)


def default_text(plan: AnalysisPlan, step_id: str) -> str:
    default = plan.step(step_id).default
    notes = [
        column.note
        for column in plan.dataset.columns
        if column.note
        and default.code
        and re.search(rf"\b{re.escape(column.name)}\b", default.code)
    ]
    return " ".join([default.label, default.rationale, default.spec, *notes])


def _rows_after(garden: Garden, change: Change, flip_universe_id: str) -> tuple[int, int] | None:
    baseline = garden.baseline
    single = single_universe(garden, change.step_id, change.to_option)
    universe = single or garden.universes.get(flip_universe_id)
    if baseline is None or universe is None:
        return None
    before, after = trace_of(baseline, change.step_id), trace_of(universe, change.step_id)
    if before is None or after is None:
        return None
    return before.rows_after, after.rows_after


def contamination_reason(
    plan: AnalysisPlan, garden: Garden, changes: list[Change], flip_universe_id: str
) -> str | None:
    for change in changes:
        step = plan.step(change.step_id)
        if step.kind != "filter":
            continue
        rows = _rows_after(garden, change, flip_universe_id)
        if rows is None or rows[1] <= rows[0]:
            continue
        words = sorted({m.lower() for m in INVALID_ROWS.findall(default_text(plan, step.id))})
        if not words:
            continue
        return (
            f"{step.title}: '{change.to_label}' re-includes {rows[1] - rows[0]} rows that the "
            f"baseline option '{step.default.label}' excluded and that the plan's own notes mark "
            f"as invalid ({', '.join(words)}); this is a contaminated-analysis flip, not a "
            "finding about the question"
        )
    return None
