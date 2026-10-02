from __future__ import annotations

import io

import pandas as pd
import pyarrow.parquet as pq

from borges.analysis import harness
from borges.analysis.models import AnalysisPlan
from borges.sandbox.backend import BranchBackend, Checkpoint

REVERSED_REASON = "reversed variable"
STATE_FILE = "state/df.parquet"
CORRELATION_LIMIT = -0.3
MIN_PAIRS = 30
GUARDED_KINDS = ("transform", "feature")


def reversed_message(column: str, correlation: float) -> str:
    return (
        f"{REVERSED_REASON}: column '{column}' correlates {correlation:.2f} with the original "
        "option's column, so the change reverses a variable's direction instead of changing "
        "the analysis"
    )


async def _raw(backend: BranchBackend, checkpoint_id: str) -> bytes:
    checkpoint = Checkpoint(id=checkpoint_id, parent_id=None, backend=backend.name)
    try:
        return await backend.read_file(checkpoint, STATE_FILE)
    except Exception:
        return await backend.read_file(checkpoint, harness.DATA_FILE)


def _names(raw: bytes) -> list[str]:
    return list(pq.read_schema(io.BytesIO(raw)).names)


def _columns(raw: bytes, wanted: list[str]) -> pd.DataFrame:
    present = [c for c in wanted if c in set(_names(raw))]
    return pd.read_parquet(io.BytesIO(raw), columns=present)


def worst_reversal(
    base: pd.DataFrame, other: pd.DataFrame, produced: list[str]
) -> tuple[str, float] | None:
    worst: tuple[str, float] | None = None
    for name in produced:
        if name not in base or name not in other:
            continue
        if not (
            pd.api.types.is_numeric_dtype(base[name]) and pd.api.types.is_numeric_dtype(other[name])
        ):
            continue
        pair = pd.concat([base[name], other[name]], axis=1, join="inner").dropna()
        if len(pair) < MIN_PAIRS:
            continue
        left, right = pair.iloc[:, 0].astype(float), pair.iloc[:, 1].astype(float)
        if left.std() == 0 or right.std() == 0:
            continue
        corr = float(left.corr(right))
        if corr < CORRELATION_LIMIT and (worst is None or corr < worst[1]):
            worst = (name, corr)
    return worst


def _added(before: list[str], after: list[str]) -> set[str]:
    return set(after) - set(before)


def _produced_pair(
    step_produces: list[str],
    base_raws: tuple[bytes, bytes],
    other_raws: tuple[bytes, bytes],
) -> list[str]:
    if step_produces:
        return list(step_produces)
    base_names = _names(base_raws[1])
    shared = _added(_names(base_raws[0]), base_names) & _added(
        _names(other_raws[0]), _names(other_raws[1])
    )
    return [c for c in base_names if c in shared]


async def find_reversal(
    backend: BranchBackend,
    plan: AnalysisPlan,
    root_id: str,
    baseline_checkpoints: list[str],
    checkpoints: list[str],
    choices: dict[str, str],
) -> str | None:
    for index, step in enumerate(plan.steps):
        if step.kind not in GUARDED_KINDS or choices[step.id] == step.default.id:
            continue
        if index >= len(checkpoints) or index >= len(baseline_checkpoints):
            continue
        try:
            base_prev = baseline_checkpoints[index - 1] if index else root_id
            other_prev = checkpoints[index - 1] if index else root_id
            base_raws = (
                await _raw(backend, base_prev),
                await _raw(backend, baseline_checkpoints[index]),
            )
            other_raws = (
                await _raw(backend, other_prev),
                await _raw(backend, checkpoints[index]),
            )
            produced = _produced_pair(list(step.produces), base_raws, other_raws)
            base = _columns(base_raws[1], produced)
            other = _columns(other_raws[1], produced)
        except Exception:
            continue
        found = worst_reversal(base, other, produced)
        if found is not None:
            return reversed_message(*found)
    return None
