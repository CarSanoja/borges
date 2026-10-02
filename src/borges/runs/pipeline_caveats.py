from __future__ import annotations

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


def report_caveats(report: Report, flip: Flip | None, threshold: float) -> list[str]:
    caveats: list[str] = []
    if report.n_failed:
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
