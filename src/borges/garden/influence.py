from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.garden.models import DecisionInfluence, Flip, Garden, Report


def decision_influence(plan: AnalysisPlan, garden: Garden) -> list[DecisionInfluence]:
    baseline = garden.baseline
    if baseline is None or baseline.result is None:
        return []
    finished = garden.finished()
    rows: list[DecisionInfluence] = []
    for step in plan.decision_steps:
        singles = [u for u in finished if u.changed == [step.id] and u.result is not None]
        deltas = [abs(u.result.estimate - baseline.result.estimate) for u in singles if u.result]
        rows.append(
            DecisionInfluence(
                step_id=step.id,
                title=step.title,
                mean_abs_delta=sum(deltas) / len(deltas) if deltas else 0.0,
                max_abs_delta=max(deltas, default=0.0),
                flips=sum(1 for u in singles if u.flipped is True),
                n_alternatives=len(step.options) - 1,
            )
        )
    return sorted(rows, key=lambda row: -row.max_abs_delta)


def robustness(garden: Garden) -> float:
    baseline = garden.baseline
    pool = [u for u in garden.finished() if u.kind != "verification"]
    if baseline is None or not pool:
        return 1.0
    return sum(1 for u in pool if u.verdict == baseline.verdict) / len(pool)


def failed_universes(garden: Garden) -> list[str]:
    lines = []
    for universe in garden.universes.values():
        if universe.status != "failed" or universe.kind == "verification":
            continue
        first = (universe.error or "unknown error").strip().splitlines()[0]
        lines.append(first)
    return lines


def build_report(plan: AnalysisPlan, garden: Garden, flip: Flip | None) -> Report:
    baseline = garden.baseline
    if baseline is None or baseline.result is None or baseline.verdict is None:
        raise ValueError("cannot build a report without a finished baseline universe")
    finished = garden.finished()
    failed = failed_universes(garden)
    return Report(
        question=plan.question,
        original_verdict=baseline.verdict,
        original_result=baseline.result,
        minimal_flip=flip,
        influences=decision_influence(plan, garden),
        robustness=robustness(garden),
        n_universes=len(finished),
        n_flipped=sum(1 for u in finished if u.flipped is True),
        n_failed=len(failed),
        failed=failed,
    )
