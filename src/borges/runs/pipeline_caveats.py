from __future__ import annotations

from borges.analysis.models import AnalysisPlan, CodingSummary
from borges.garden.models import Flip, Report
from borges.garden.plausibility import IMPLAUSIBLE_REASON

MIRROR_TOLERANCE = 0.05


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
    mirrored = mirror_caveat(flip, threshold)
    if mirrored:
        caveats.append(mirrored)
    return caveats


def analysis_caveats(plan: AnalysisPlan) -> list[str]:
    return [
        f"The starting point may not be exactly your analysis, so read the original result with "
        f"care: {gap}."
        for gap in plan.analysis_gaps
    ]


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
