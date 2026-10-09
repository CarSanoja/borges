"""A flip that turns on how extreme values are handled, said in the figures the run computed.

An A/B garden flipped from SHIP (0.656, p=0.002) to DON'T SHIP (10.44, p=0.12) when the revenue
winsorizing was dropped: a few sessions of 48k to 61k carry the difference, and nothing said so
(r_20261009T003247_06812b). The profile keeps the median, mean, standard deviation and maximum of
a column, not its quantiles or a count of the rows above a cut, so the note names the column's
spread and the two results; the rows are counted only when the options differ in the rows kept.
"""

from __future__ import annotations

import re

from borges.analysis.models import AnalysisPlan, ColumnProfile, Step
from borges.garden.models import Change, Flip

OUTLIER_STEP = re.compile(
    r"winsor|trim|outlier|\bclip|\bcap(?:ped|ping)?\b|truncat|extreme|top[- ]?cod", re.IGNORECASE
)
HEAVY_TAIL = 5.0


def _step_text(step: Step) -> str:
    return " ".join([step.id, step.title, *(f"{o.id} {o.label} {o.spec}" for o in step.options)])


def _column(plan: AnalysisPlan, step: Step) -> ColumnProfile | None:
    text = _step_text(step).lower()
    found = [
        c
        for c in plan.dataset.columns
        if {"mean", "std", "p50", "max"} <= set(c.summary)
        and re.search(rf"(?<![a-z0-9]){re.escape(c.name.lower())}(?![a-z0-9])", text)
    ]
    return max(found, key=lambda c: len(c.name), default=None)


def _outlier_change(plan: AnalysisPlan, flip: Flip) -> tuple[Change, Step] | None:
    for change in flip.changes:
        step = plan.step(change.step_id)
        if OUTLIER_STEP.search(f"{step.id} {step.title} {change.to_label}"):
            return change, step
    return None


def _heavy(column: ColumnProfile) -> bool:
    mean, std = float(column.summary["mean"]), float(column.summary["std"])
    return std > 0 and (float(column.summary["max"]) - mean) / std > HEAVY_TAIL


def _number(value: float | str) -> str:
    number = float(value)
    return f"{number:,.0f}" if abs(number) >= 1000 else f"{number:.4g}"


def extreme_rows_note(plan: AnalysisPlan, flip: Flip | None) -> str | None:
    if flip is None:
        return None
    found = _outlier_change(plan, flip)
    if found is None:
        return None
    change, step = found
    column = _column(plan, step)
    if column is None or not _heavy(column):
        return None
    before, after = flip.baseline_result, flip.flipped_result
    summary = column.summary
    note = (
        f"The flip turns on how the extreme values of {column.name} are handled "
        f"('{change.to_label}' in '{step.title}'): the median is {_number(summary['p50'])} but the "
        f"maximum is {_number(summary['max'])} (mean {_number(summary['mean'])}, standard "
        f"deviation {_number(summary['std'])}). With the original handling the estimate is "
        f"{before.estimate:.3g} (p={before.p_value:.2g}); with the change it is "
        f"{after.estimate:.3g} (p={after.p_value:.2g}, interval {after.ci_low:.3g} to "
        f"{after.ci_high:.3g})."
    )
    if abs(after.estimate) > abs(before.estimate) and after.p_value > before.p_value:
        note += " The larger estimate is too noisy to be significant: a few rows carry it."
    if before.n != after.n:
        note += f" The change moves the sample from {before.n} to {after.n} rows."
    return note
