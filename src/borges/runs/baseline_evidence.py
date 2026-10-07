"""Where the step-by-step fit and the reference fit part, in the raw data's own rows.

fertility_vote on 7 October, runs 25 and 26: the starting point fitted 301 women against the
reference's 303, and the repairer, given the specs, the code and row counts, proposed nothing or
an irrelevant fix. The rows one fit has and the other lacks are named by the row key, with their
raw values, and the mean of every design column of both fits is shown, so that a reversed or a
-1/+1 coding shows too.
"""

from __future__ import annotations

import io

import pandas as pd

from borges.garden.fit_summary import fit_summary
from borges.garden.models import Universe

SHOWN = 8


def as_text(frame: pd.DataFrame) -> list[dict[str, str]]:
    shown = frame.astype(object).where(frame.notna(), "missing")
    return [{str(k): str(v) for k, v in row.items()} for row in shown.to_dict("records")]


def _rows(frame: pd.DataFrame, names: pd.Series, keys: list[str]) -> list[dict[str, str]]:
    return as_text(frame[names.isin(keys[:SHOWN])])


def fit_difference(
    data: bytes | None, key: str | None, ours: Universe, theirs: dict[str, object]
) -> dict[str, object] | None:
    mine = fit_summary(ours.traces)
    found: dict[str, object] = {}
    if mine.get("means") or theirs.get("means"):
        found["design_means"] = {
            "step_by_step": mine.get("means"),
            "reference": theirs.get("means"),
        }
    a, b = mine.get("row_keys"), theirs.get("row_keys")
    if data is None or key is None or not isinstance(a, list) or not isinstance(b, list):
        return found or None
    only_reference = sorted(set(map(str, b)) - set(map(str, a)))
    only_ours = sorted(set(map(str, a)) - set(map(str, b)))
    frame = pd.read_parquet(io.BytesIO(data))
    if key not in frame.columns:
        return found or None
    names = frame[key].astype(str)
    found.update(
        row_key=key,
        n_only_in_reference=len(only_reference),
        rows_only_in_reference=_rows(frame, names, only_reference),
        n_only_in_step_by_step=len(only_ours),
        rows_only_in_step_by_step=_rows(frame, names, only_ours),
    )
    return found
