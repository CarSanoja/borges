from __future__ import annotations

from borges.analysis.models import AnalysisResult
from borges.garden.models import Flip
from borges.runs.models import RunSnapshot, UniverseDetail


def result_line(result: AnalysisResult) -> str:
    return (
        f"estimate {result.estimate:+.4f}, 95% CI [{result.ci_low:+.4f}, "
        f"{result.ci_high:+.4f}], p = {result.p_value:.4g}, n = {result.n}"
    )


def flip_lines(flip: Flip) -> list[str]:
    lines = [f"Minimal flip: {flip.baseline_verdict} -> {flip.flipped_verdict}"]
    for change in flip.changes:
        lines.append(f"  - {change.step_title}: {change.from_option} -> {change.to_label}")
        lines.append(f"      why: {change.rationale}")
        if change.source:
            lines.append(f"      source: {change.source}")
    lines.append(f"  flipped result: {result_line(flip.flipped_result)}")
    reproduced = {None: "not checked", True: "yes", False: "no"}[flip.reproduced]
    lines.append(f"  reproduced: {reproduced}")
    return lines


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
            lines.append("Minimal flip: none found")
        lines.append(
            f"Robustness: {report.robustness:.0%} of {report.n_universes} universes "
            f"keep the original verdict ({report.n_flipped} flipped)"
        )
    usage = snapshot.usage
    lines.append(
        f"Universes: {usage.universes}, checkpoints: {usage.checkpoints}, "
        f"LLM calls: {usage.llm_calls} ({usage.cached_calls} cached)"
    )
    lines.append(
        f"Tokens: {usage.tokens_in} in / {usage.tokens_out} out, cost: ${usage.cost_usd:.4f}"
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
