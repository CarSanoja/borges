"""Where the step-by-step chain loses the rows the reference fits, and what they hold there.

fertility_vote on 7 October, run 28: told that WorkerID 15 and 16 were fitted by the reference and
not by the starting point, the repairer reasoned that the cycle-day step set their days and blamed
the window filter instead. The chain's own state after each step is in its checkpoints, so the
step after which the rows are gone is named, with the values the earlier steps built for them just
before it: there the two women had no cycle day, where the cycle-day spec sets 11 and 18. Rows
that every step keeps were left out by the model's own fit, and are shown as the model received
them.
"""

from __future__ import annotations

import io

import pandas as pd

from borges.analysis.models import AnalysisPlan
from borges.garden.fit_summary import fit_summary
from borges.garden.models import Universe
from borges.garden.reversal import _raw
from borges.runs.baseline_evidence import SHOWN, as_text, fit_difference

MAX_COLUMNS = 12


def _built(frame: pd.DataFrame, raw: list[str], key: str, keys: set[str]) -> list[dict[str, str]]:
    columns = [c for c in frame.columns if c not in raw][:MAX_COLUMNS]
    rows = frame[frame[key].astype(str).isin(keys)]
    return as_text(rows[[key, *columns]])


async def where_lost(
    backend: object, plan: AnalysisPlan, chain: Universe, key: str, keys: list[str], raw: bytes
) -> list[dict[str, object]]:
    previous = pd.read_parquet(io.BytesIO(raw))
    columns = list(previous.columns)
    remaining, found = set(keys[:SHOWN]), []
    for step, checkpoint in zip(plan.steps, chain.checkpoints, strict=False):
        if not remaining:
            break
        try:
            frame = pd.read_parquet(io.BytesIO(await _raw(backend, checkpoint)))  # type: ignore[arg-type]
        except Exception:
            return found
        if key not in frame.columns:
            return found
        gone = remaining - set(frame[key].astype(str))
        if gone and step.kind != "model":
            found.append(
                {
                    "lost_after_step": step.id,
                    "built_values_just_before": _built(previous, columns, key, gone),
                }
            )
            remaining -= gone
        previous = frame
    if remaining:
        model = next((s.id for s in reversed(plan.steps) if s.kind == "model"), None)
        found.append(
            {
                "kept_by_every_step_then_left_out_by_the_fit_of": model,
                "values_the_model_received": _built(previous, columns, key, remaining),
            }
        )
    return found


async def located_difference(
    executor: object,
    plan: AnalysisPlan,
    data: bytes | None,
    key: str | None,
    chain: Universe,
    theirs: dict[str, object],
) -> dict[str, object] | None:
    found = fit_difference(data, key, chain, theirs)
    backend = getattr(executor, "backend", None)
    if not found or backend is None or data is None or key is None:
        return found
    ours = fit_summary(chain.traces).get("row_keys")
    if not isinstance(ours, list):
        return found
    lost = sorted({str(k) for k in theirs.get("row_keys") or []} - set(map(str, ours)))
    if lost and chain.checkpoints:
        found["where_the_step_by_step_code_loses_them"] = await where_lost(
            backend, plan, chain, key, lost, data
        )
    return found
