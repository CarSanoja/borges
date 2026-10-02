from __future__ import annotations

from borges.garden.models import Flip

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
