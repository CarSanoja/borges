from __future__ import annotations

from borges.analysis.models import AnalysisResult, CodingSummary
from borges.garden.models import Flip, Report, SearchSummary
from borges.llm.local_models import LOCAL_LABEL
from borges.runs.models import RunSnapshot, UniverseDetail

KIND_NOTES = {
    "significance": " (significance only: the estimate stays on the same side, p crosses 0.05)",
    "direction": " (direction: the estimate crosses the threshold)",
}


def p_text(p_value: float) -> str:
    return "p < 1e-16" if p_value < 1e-16 else f"p = {p_value:.4g}"


def result_line(result: AnalysisResult) -> str:
    return (
        f"estimate {result.estimate:+.4f}, 95% CI [{result.ci_low:+.4f}, "
        f"{result.ci_high:+.4f}], {p_text(result.p_value)}, n = {result.n}"
    )


def flip_lines(flip: Flip) -> list[str]:
    lines = [
        f"Smallest flip found{KIND_NOTES.get(flip.kind or '', '')}: "
        f"{flip.baseline_verdict} -> {flip.flipped_verdict}"
    ]
    for change in flip.changes:
        lines.append(f"  - {change.step_title}: {change.from_option} -> {change.to_label}")
        lines.append(f"      why: {change.rationale}")
        if change.source:
            lines.append(f"      cited by the model, not checked: {change.source}")
    if flip.estimand_change:
        lines.append(f"  estimand change: this flip {flip.estimand_change}")
    lines.append(f"  flipped result: {result_line(flip.flipped_result)}")
    reproduced = {None: "not checked", True: "yes", False: "no"}[flip.reproduced]
    lines.append(f"  reproduced: {reproduced}")
    return lines


def recording_label(scripted: bool, live: bool) -> str:
    if scripted and live:
        return "recorded (scripted and live)"
    if scripted:
        return "recorded"
    return "live recording only" if live else "no recording"


BASIS_LABELS = {
    "design_weighted": "design-weighted",
    "distinct_results": "share of distinct results",
    "none": "no universes",
}


def robustness_line(report: Report) -> str:
    distinct = report.n_distinct_results or report.n_universes
    line = (
        f"Robustness: {report.robustness:.0%} ({BASIS_LABELS[report.robustness_basis]}); "
        f"{report.n_universes} universes explored, {distinct} distinct results, "
        f"{report.n_flipped} flipped"
    )
    if report.n_failed:
        line += (
            f"; {report.n_failed} more failed and are untested "
            f"({report.n_universes} of {report.n_universes + report.n_failed} attempted completed)"
        )
    if report.robustness_rating_reason:
        line += f"; not rated ({report.robustness_rating_reason})"
    return line


def search_line(search: SearchSummary) -> str:
    level = "level" if search.levels_explored == 1 else "levels"
    line = (
        f"Search budget: {search.universes_used} of {search.universe_budget} universes used, "
        f"{search.levels_explored} {level} explored, at most "
        f"{search.max_combinations_per_level} combinations per level"
    )
    if search.sample_draws:
        line += f"; {search.sample_draws} uniform random draws from the grid"
    return line + (
        "; the budget ran out before the search finished" if search.budget_exhausted else ""
    )


def coding_line(coding: CodingSummary) -> str:
    line = (
        f"Coding: {coding.options} options written, {coding.smoke_tested} smoke-tested on a "
        f"sample, {coding.repaired_after_smoke} repaired after a runtime error, "
        f"{coding.failed} failed"
    )
    if coding.options_dropped_by_judge:
        line = f"{line}; {coding.options_dropped_by_judge} dropped by the defensibility judge"
    if coding.defaults_replaced:
        line = f"{line}; {len(coding.defaults_replaced)} conventional options replaced by the judge"
    if not coding.steps_reviewed:
        return line
    return (
        f"{line}; {coding.steps_reviewed} steps reviewed, {coding.options_flagged} options "
        f"flagged, {coding.options_dropped_by_review} dropped"
    )


def summary_lines(snapshot: RunSnapshot) -> list[str]:
    lines = [f"Run {snapshot.run_id} ({snapshot.status})"]
    if snapshot.title:
        lines.append(snapshot.title)
    lines.append(f"Question: {snapshot.question}")
    report = snapshot.report
    if report is not None:
        lines.append(f"Original verdict: {report.original_verdict}")
        lines.append(f"  {result_line(report.original_result)}")
        if report.minimal_flip is not None:
            lines.extend(flip_lines(report.minimal_flip))
        else:
            lines.append(
                "Smallest flip found: none, only the default analysis ran"
                if report.n_universes <= 1
                else "Smallest flip found: none within the search budget"
            )
        lines.append(robustness_line(report))
        if report.n_failed:
            lines.append(
                f"  {report.n_universes + report.n_failed} explored, "
                f"{report.n_failed} could not run"
            )
        if report.search is not None:
            lines.append(search_line(report.search))
        if report.coding is not None:
            lines.append(coding_line(report.coding))
        lines.extend(f"Caveat: {caveat}" for caveat in report.caveats)
    usage = snapshot.usage
    scripted = snapshot.llm == "scripted"
    calls = f"{usage.llm_calls} scripted" if scripted else str(usage.llm_calls)
    lines.append(
        f"Universes: {usage.universes}, checkpoints: {usage.checkpoints}, "
        f"LLM calls: {calls} ({usage.cached_calls} cached)"
    )
    if snapshot.llm == "local":
        lines.append(f"Model: {LOCAL_LABEL}")
        lines.append(
            f"Tokens: {usage.tokens_in} in / {usage.tokens_out} out, cost: $0.0000 (local)"
        )
    elif scripted:
        lines.append("Tokens: 0 in / 0 out, cost: $0.0000 (scripted replay, no model called)")
    else:
        lines.append(
            f"Tokens: {usage.tokens_in} in / {usage.tokens_out} out, "
            f"estimated cost: ${usage.cost_usd:.4f} "
            "(token counts x list prices, not a billed amount)"
        )
    if snapshot.error:
        lines.append(f"Error: {snapshot.error}")
    return lines


def universe_lines(detail: UniverseDetail) -> list[str]:
    universe = detail.universe
    lines = [f"Universe {universe.id} ({universe.kind}, {universe.status})"]
    if universe.verdict:
        flipped = " (flipped)" if universe.flipped else ""
        lines.append(f"Verdict: {universe.verdict}{flipped}")
    if universe.result is not None:
        lines.append(f"Result: {result_line(universe.result)}")
    if universe.error:
        lines.append(f"Error: {universe.error}")
    lines.append(f"Checkpoints: {', '.join(universe.checkpoints) or 'none'}")
    for item in detail.steps:
        marker = "*" if item.changed else " "
        lines.append(f"{marker} {item.step.title}: {item.option.label}")
        if item.trace is not None:
            lines.append(f"    rows {item.trace.rows_before} -> {item.trace.rows_after}")
        if item.option.code:
            lines.extend(f"    | {row}" for row in item.option.code.splitlines())
    lines.append(f"Reproduce: {detail.reproduce_command}")
    return lines
