from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.garden.models import DuplicateOption, Flip, NoopOption
from borges.garden.report_duplicate_notes import (
    dead_step_notes,
    duplicate_notes,
    flip_attribution_notes,
)
from borges.garden.robustness import RobustnessFigures


def failed_tail(n_completed: int, n_failed: int) -> str:
    if not n_failed:
        return ""
    return (
        f" The share is over the {n_completed} universes that completed; {n_failed} more "
        f"failed and are untested ({n_completed} of {n_completed + n_failed} attempted completed)."
    )


def figure_caveats(
    plan: AnalysisPlan,
    n_universes: int,
    figures: RobustnessFigures,
    noops: list[NoopOption],
    flip: Flip | None,
    contaminated: list[Flip],
    duplicates: list[DuplicateOption] | None = None,
    n_failed: int = 0,
) -> list[str]:
    duplicates = duplicates or []
    notes: list[str] = []
    if figures.n_distinct and figures.n_distinct < n_universes:
        notes.append(
            f"{n_universes} universes ran but only {figures.n_distinct} gave distinct results; "
            "universes with identical results are counted once in the robustness share."
        )
    for noop in noops:
        notes.append(
            f"The option '{noop.label}' ({noop.step_id}) is a no-op: {noop.reason}. It is "
            "excluded from the robustness share and from the flip search."
        )
    notes.extend(dead_step_notes(plan, noops))
    notes.extend(duplicate_notes(duplicates))
    notes.extend(flip_attribution_notes(flip, duplicates))
    if figures.basis == "design_weighted" and figures.beam is not None:
        notes.append(
            f"The {figures.design:.0%} robustness estimate is the share of the analysis grid that "
            f"agrees with the original verdict; it was sampled as follows: {figures.design_note}. "
            "The universes the beam search explored are the ones closest to flipping, so their own "
            "agreement share leans toward flips and is not used as the estimate."
            + failed_tail(n_universes, n_failed)
        )
    if flip is not None and flip.estimand_change:
        notes.append(f"The minimal flip {flip.estimand_change}.")
    if len(contaminated) == 1:
        notes.append(
            f"A flip was found but is not the headline: {contaminated[0].contamination_reason}."
        )
    elif contaminated:
        reasons = "; ".join(str(f.contamination_reason) for f in contaminated)
        notes.append(f"{len(contaminated)} flips were found and none is the headline: {reasons}.")
    return notes
