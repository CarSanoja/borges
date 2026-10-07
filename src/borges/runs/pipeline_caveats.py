from __future__ import annotations

from borges.analysis.models import AnalysisPlan, CodingSummary
from borges.garden.degenerate import DEGENERATE_REASON
from borges.garden.mirror import MIRROR_REASON
from borges.garden.models import Flip, Report
from borges.garden.plausibility import IMPLAUSIBLE_REASON

MIRROR_TOLERANCE = 0.05
DEPARTURE = "The starting point is not exactly your analysis: in the step '{title}', "


def mirror_caveat(flip: Flip | None, threshold: float) -> str | None:
    if flip is None or flip.kind != "direction":
        return None
    before, after = flip.baseline_result, flip.flipped_result
    if before.n != after.n:
        return None
    base, flipped = before.estimate - threshold, after.estimate - threshold
    if base == 0 or base * flipped >= 0:
        return None
    if abs(base + flipped) > MIRROR_TOLERANCE * abs(base):
        return None
    return (
        f"the flipped estimate mirrors the original ({before.estimate:+.4f} vs "
        f"{after.estimate:+.4f}, same rows): check that the changed option did not reverse a "
        "variable's direction"
    )


def _key(text: str) -> str:
    return " ".join(text.lower().split()).rstrip(".")


def merge_caveats(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for caveat in (c for group in groups for c in group):
        key = _key(caveat)
        if key not in seen:
            seen.add(key)
            merged.append(caveat)
    return merged


UNTESTED = (
    "Only the default analysis ran: no alternative option survived judging and coding, so this "
    "run did not test whether the decision is robust."
)


def report_caveats(
    report: Report, flip: Flip | None, threshold: float, failed: str | None = None
) -> list[str]:
    caveats: list[str] = []
    if flip is None and report.n_universes <= 1:
        caveats.append(UNTESTED)
    if failed is not None:
        caveats.append(failed)
    elif report.n_failed:
        caveats.append(
            f"{report.n_failed} universes could not run and are left out of the robustness figure."
        )
    implausible = sum(1 for line in report.failed if line.startswith(IMPLAUSIBLE_REASON))
    if implausible:
        caveats.append(
            f"{implausible} universes produced an implausible estimate (far outside the "
            "scale of the baseline) and were excluded as broken implementations, not counted "
            "as flips."
        )
    degenerate = sum(1 for line in report.failed if line.startswith(DEGENERATE_REASON))
    if degenerate:
        caveats.append(
            f"{degenerate} universes gave a fit that cannot be estimated on this data (an interval "
            "over 100 times wider than the baseline's, as with separation in a logistic model) and "
            "were left out, not counted as flips."
        )
    reversed_coding = sum(1 for line in report.failed if line.startswith(MIRROR_REASON))
    if reversed_coding:
        caveats.append(
            f"{reversed_coding} universes gave the starting point's result with its sign reversed "
            "on the same rows with the same p-value: their options code the other group as 1, "
            "the same analysis, so they were left out and not counted as flips."
        )
    mirrored = mirror_caveat(flip, threshold)
    if mirrored:
        caveats.append(mirrored)
    return caveats


GAP_PREFIX = "The starting point may not be exactly your analysis"


def analysis_caveats(plan: AnalysisPlan) -> list[str]:
    return [
        f"{GAP_PREFIX}, so read the original result with care: {gap}." for gap in plan.analysis_gaps
    ]


def default_departures(planned: AnalysisPlan, coded: AnalysisPlan) -> list[str]:
    """On a run from the user's analysis, a step whose default could not run and was replaced
    leaves an original result that is not the user's; the smoke note alone does not say so."""
    found = []
    by_id = {step.id: step for step in coded.steps}
    for step in planned.steps:
        now = by_id.get(step.id)
        if not step.options or now is None or not now.options:
            continue
        if now.default.id != step.default.id:
            found.append(
                DEPARTURE.format(title=step.title)
                + f"'{step.default.label}' could not run and '{now.default.label}' was used "
                "instead, so the original result is that of a changed analysis."
            )
    return found


def judge_caveats(coding: CodingSummary) -> list[str]:
    replaced = [
        f"The defensibility judge rejected a conventional option and the original analysis uses "
        f"the best accepted alternative instead ({item})."
        for item in coding.defaults_replaced
    ]
    disputed = [
        f"The defensibility judge disputes a conventional option that had no accepted "
        f"replacement, so it was kept; read the original result with care ({item})."
        for item in coding.defaults_disputed
    ]
    kept = [
        f"The defensibility judge disputes a choice of your own analysis; it stays the starting "
        f"point, because the question is how fragile your analysis is, and the alternatives are "
        f"tested against it ({item})."
        for item in coding.defaults_kept
    ]
    return replaced + disputed + kept
