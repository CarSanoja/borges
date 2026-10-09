"""A produced column whose origin moved.

fertility_social, r_20261009T074443_86006a (9 October 2026): an adversary filter recounted
cycle_day as the days to ovulation; the orientation check found it reversed (r -0.93), the repair
negated it, and the column then followed the default's (r +0.93) about 14 days lower. The next
step read it with the default's windows (7-14 high, 17-25 low), so "high fertility" became the
luteal phase, and the run reported that universe as a sign-reversing flip. A whole-number column
that follows the default's one for one but sits more than SHIFTED_SDS standard deviations away
counts from another origin, and later steps that cut it at fixed values select other rows.

A bank run (r_20261009T085134_401637) lost an option that counted days since sign-up from another
date: the column only entered a linear model, where the shift moves the intercept and nothing
else. The check applies to a column that some option of the plan compares with a value.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

import numpy as np

from borges.analysis.harness_missing_cut import compared_names
from borges.analysis.models import Step

MIN_PAIRS = 30
SHIFTED_SDS = 1.5
FOLLOWS_R = 0.9
SLOPE_LOW, SLOPE_HIGH = 0.8, 1.25
SHIFTED_TEMPLATE = (
    "column '{name}' follows the default option's one for one but sits {shift:+.1f} away from it "
    "on the same rows (its spread is {sd:.1f}): it counts from another origin, and later steps "
    "cut it at the default's values, so they would select other rows. Count from the default's "
    "origin and keep its scale"
)


def _probe(effects: dict[str, Any] | None, name: str) -> dict[str, Any] | None:
    column = ((effects or {}).get("columns") or {}).get(name)
    probe = column.get("probe") if isinstance(column, dict) else None
    return probe if isinstance(probe, dict) else None


def probe_pairs(
    default: dict[str, Any] | None, other: dict[str, Any] | None, name: str
) -> tuple[np.ndarray, np.ndarray] | None:
    """The column's values under both options on the probe rows they share."""
    left, right = _probe(default, name), _probe(other, name)
    if not left or not right:
        return None
    pairs = [
        (float(left[k]), float(right[k]))
        for k in left.keys() & right.keys()
        if left[k] is not None
        and right[k] is not None
        and math.isfinite(float(left[k]))
        and math.isfinite(float(right[k]))
    ]
    if len(pairs) < MIN_PAIRS:
        return None
    xs, ys = np.array(pairs).T
    return xs, ys


def cut_names(steps: Iterable[Step]) -> set[str]:
    """Columns that some option of the plan compares with a value."""
    return {n for s in steps for o in s.options if o.code for n in compared_names(o.code)}


def shifted_error(
    name: str, default: dict[str, Any] | None, other: dict[str, Any] | None
) -> str | None:
    pairs = probe_pairs(default, other, name)
    if pairs is None:
        return None
    xs, ys = pairs
    sd, spread = float(np.std(xs)), float(np.std(ys))
    whole = np.allclose(xs, np.round(xs)) and np.allclose(ys, np.round(ys))
    if not whole or sd == 0 or spread == 0:
        return None
    follows = float(np.corrcoef(xs, ys)[0, 1]) >= FOLLOWS_R
    shift = float(np.median(ys - xs))
    if not follows or not SLOPE_LOW <= spread / sd <= SLOPE_HIGH or abs(shift) <= SHIFTED_SDS * sd:
        return None
    return SHIFTED_TEMPLATE.format(name=name, shift=shift, sd=sd)
