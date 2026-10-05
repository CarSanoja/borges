"""Options that re-include rows the plan's own notes mark as invalid. Their flips are not findings
about the question (contamination.py), and they are not counted in the robustness share either:
a checkout garden whose baseline excluded internal and short sessions (068fa85) reported no
defensible flip beside "40% of the grid agrees", because the two options that re-included those
rows were counted as reversals."""

from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.garden.contamination import INVALID_ROWS, default_text
from borges.garden.models import Garden, NoopOption
from borges.garden.noop import single_universe, trace_of


def contaminated_options(plan: AnalysisPlan, garden: Garden) -> list[NoopOption]:
    baseline = garden.baseline
    if baseline is None:
        return []
    found: list[NoopOption] = []
    for step in plan.decision_steps:
        words = sorted({m.lower() for m in INVALID_ROWS.findall(default_text(plan, step.id))})
        before = trace_of(baseline, step.id)
        if step.kind != "filter" or not words or before is None:
            continue
        for option in step.options:
            single = single_universe(garden, step.id, option.id)
            after = trace_of(single, step.id) if single is not None else None
            if option.is_default or after is None or after.rows_after <= before.rows_after:
                continue
            found.append(
                NoopOption(
                    step_id=step.id,
                    option_id=option.id,
                    label=option.label,
                    reason=(
                        f"re-includes {after.rows_after - before.rows_after} rows that the "
                        f"baseline option '{step.default.label}' excluded and that the plan's own "
                        f"notes mark as invalid ({', '.join(words)})"
                    ),
                )
            )
    return found


def contaminated_notes(options: list[NoopOption]) -> list[str]:
    return [
        f"The option '{o.label}' {o.reason}, so its universes are excluded from the robustness "
        "share, as its flips are from the headline."
        for o in options
    ]
