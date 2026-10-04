from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.garden.models import DuplicateOption, Flip, NoopOption
from borges.garden.report_duplicate_notes import (
    dead_step_notes,
    duplicate_notes,
    flip_attribution_notes,
)
from borges.garden.robustness import RobustnessFigures


def figure_caveats(
    plan: AnalysisPlan,
    n_universes: int,
    figures: RobustnessFigures,
    noops: list[NoopOption],
    flip: Flip | None,
    contaminated: Flip | None,
    duplicates: list[DuplicateOption] | None = None,
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
            f"Robustness headline is design-weighted ({figures.design:.0%}): "
            f"{figures.design_note}. The share among the explored universes is "
            f"{figures.beam:.0%}, but the beam search samples the universes that are closest to "
            "flipping, so that figure leans toward flips."
        )
    if flip is not None and flip.estimand_change:
        notes.append(f"The minimal flip {flip.estimand_change}.")
    if contaminated is not None:
        notes.append(
            f"A flip was found but is not the headline: {contaminated.contamination_reason}."
        )
    return notes
