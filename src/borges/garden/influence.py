from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.garden.comparable import comparable, scale_caveats
from borges.garden.contaminated_options import contaminated_notes, contaminated_options
from borges.garden.duplicates import duplicate_options
from borges.garden.estimand import estimand_changes
from borges.garden.exposure_spread import exposure_spread_notes
from borges.garden.flips import contaminated_flips
from borges.garden.measure import measure_caveats, rule_measure_caveats
from borges.garden.models import DecisionInfluence, Flip, Garden, Report
from borges.garden.noop import noop_options
from borges.garden.report_notes import figure_caveats
from borges.garden.reversal import REVERSED_REASON
from borges.garden.robustness import robustness_figures


def decision_influence(plan: AnalysisPlan, garden: Garden) -> list[DecisionInfluence]:
    baseline = garden.baseline
    if baseline is None or baseline.result is None:
        return []
    finished = garden.finished()
    rows: list[DecisionInfluence] = []
    for step in plan.decision_steps:
        singles = [
            u
            for u in finished
            if u.changed == [step.id] and u.result is not None and comparable(baseline, u)
        ]
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


def reversal_caveats(garden: Garden) -> list[str]:
    reasons = {
        (u.error or "").strip().splitlines()[0]
        for u in garden.universes.values()
        if u.status == "failed" and (u.error or "").startswith(REVERSED_REASON)
    }
    return [
        f"A universe was excluded from the robustness and influence figures: {reason}."
        for reason in sorted(reasons)
    ]


def build_report(plan: AnalysisPlan, garden: Garden, flip: Flip | None) -> Report:
    baseline = garden.baseline
    if baseline is None or baseline.result is None or baseline.verdict is None:
        raise ValueError("cannot build a report without a finished baseline universe")
    finished = garden.finished()
    failed = failed_universes(garden)
    noops = noop_options(plan, garden)
    duplicates = duplicate_options(plan, garden, noops)
    invalid = contaminated_options(plan, garden)
    figures = robustness_figures(plan, garden, [*noops, *duplicates, *invalid])
    estimands = estimand_changes(plan, garden)
    tainted = contaminated_flips(plan, garden)
    contaminated = tainted[0] if tainted else None
    return Report(
        question=plan.question,
        original_verdict=baseline.verdict,
        original_result=baseline.result,
        minimal_flip=flip,
        influences=decision_influence(plan, garden),
        robustness=figures.headline,
        n_universes=len(finished),
        n_flipped=sum(1 for u in finished if u.flipped is True),
        n_distinct_results=figures.n_distinct,
        robustness_basis=figures.basis,
        robustness_beam=figures.beam,
        robustness_design=figures.design,
        robustness_design_note=figures.design_note,
        robustness_low=figures.low,
        robustness_high=figures.high,
        robustness_rating=figures.rating,
        robustness_rating_reason=figures.rating_reason,
        noop_options=noops,
        duplicate_options=duplicates,
        estimand_changes=estimands,
        contaminated_flip=contaminated,
        contaminated_flips=tainted,
        n_attempted=len(finished) + len(failed),
        n_failed=len(failed),
        failed=failed,
        caveats=[
            *reversal_caveats(garden),
            *figure_caveats(
                plan, len(finished), figures, noops, flip, tainted, duplicates, len(failed)
            ),
            *exposure_spread_notes(plan, garden),
            *contaminated_notes(invalid),
            *rule_measure_caveats(plan, garden),
            *measure_caveats(plan, garden),
            *scale_caveats(garden),
        ],
    )
