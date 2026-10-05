from __future__ import annotations

from typing import TYPE_CHECKING, Any

from borges.analysis.models import AnalysisPlan, AnalysisResult
from borges.analysis.prompts import compact_json
from borges.garden.models import Garden, Universe

if TYPE_CHECKING:
    from borges.runs.judged_ledger import JudgedLedger

NARRATOR_INPUT_BUDGET_TOKENS = 150_000
CHARS_PER_TOKEN = 3.5
REASON_CHARS = 300
ERROR_CHARS = 160


def estimate_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN) + 1


def _sig(value: float) -> float:
    return float(f"{value:.4g}")


def _changes(plan: AnalysisPlan, universe: Universe) -> list[str]:
    out = []
    for step_id in universe.changed:
        step = plan.step(step_id)
        out.append(f"{step.title}: {step.option(universe.choices[step_id]).label}")
    return out


def _result(result: AnalysisResult, detail: int) -> dict[str, Any]:
    if detail == 0:
        return {
            "estimate": _sig(result.estimate),
            "ci": [_sig(result.ci_low), _sig(result.ci_high)],
            "p": _sig(result.p_value),
            "n": result.n,
        }
    return {"estimate": _sig(result.estimate), "p": _sig(result.p_value)}


def _row(plan: AnalysisPlan, universe: Universe, detail: int) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": universe.id,
        "kind": universe.kind,
        "changes": _changes(plan, universe),
    }
    if universe.status == "done" and universe.result is not None:
        row.update(_result(universe.result, detail))
        row["verdict"] = universe.verdict
        if universe.flipped:
            row["flipped"] = True
    else:
        row["failed"] = (universe.error or "unknown error").strip().splitlines()[0][:ERROR_CHARS]
    return row


def _judge_rows(plan: AnalysisPlan, judged: JudgedLedger | None) -> list[dict[str, Any]]:
    if judged is None:
        return []
    rows = []
    for step_id, entries in judged.entries.items():
        title = plan.step(step_id).title
        kept = {o.id for o in plan.step(step_id).options}
        for entry in entries:
            if entry.judgement.accepted and entry.option.id not in kept:
                continue
            rows.append(
                {
                    "step": title,
                    "option": entry.option.label,
                    "origin": entry.option.origin,
                    "accepted": entry.judgement.accepted,
                    "defensibility": entry.judgement.defensibility,
                    "reason": entry.judgement.reason[:REASON_CHARS],
                }
            )
    return rows


def _universes(plan: AnalysisPlan, garden: Garden, detail: int) -> list[dict[str, Any]]:
    rows = [u for u in garden.universes.values() if u.kind != "verification"]
    if detail >= 2:
        baseline = garden.baseline_id
        rows = [u for u in rows if u.id == baseline or u.flipped or u.status == "failed"]
    return [_row(plan, u, detail) for u in rows]


def garden_digest(
    plan: AnalysisPlan,
    garden: Garden,
    judged: JudgedLedger | None,
    caveats: list[str],
    budget: int = NARRATOR_INPUT_BUDGET_TOKENS,
    fixed_tokens: int = 0,
) -> tuple[dict[str, Any], int]:
    """Every universe, the judge verdicts and the caveats, thinned only when over the budget."""
    digest: dict[str, Any] = {}
    detail = 0
    while True:
        digest = {
            "universes": _universes(plan, garden, detail),
            "judge_verdicts": _judge_rows(plan, judged),
            "caveats": caveats,
            "detail": ["full", "estimate and p only", "baseline, flipped and failed only"][detail],
        }
        used = fixed_tokens + estimate_tokens(compact_json(digest))
        if used <= budget or detail == 2:
            return digest, used
        detail += 1
