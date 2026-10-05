"""Universes whose model z-scores the outcome.

A decision rule on a standardised coefficient makes the code z-score the outcome as well as the
predictors (`standardize_for_rule`). The marp_norms options at a491fe1 described a raw outcome while
their code scaled it, and an independent refit flagged the mismatch; the report now says so.
"""

from __future__ import annotations

from borges.analysis.model_spec.render_fit import SCALED_OUTCOME
from borges.garden.models import Garden


def scaled_outcomes(garden: Garden) -> tuple[int, list[str]]:
    names: set[str] = set()
    universes = 0
    for universe in garden.universes.values():
        found = [
            trace.note.split(SCALED_OUTCOME, 1)[1].split(";")[0]
            for trace in universe.traces
            if SCALED_OUTCOME in trace.note
        ]
        if found:
            universes += 1
            names.update(found)
    return universes, sorted(names)


def scaled_outcome_caveats(garden: Garden) -> list[str]:
    universes, names = scaled_outcomes(garden)
    if not universes:
        return []
    quoted = ", ".join(f"'{n}'" for n in names)
    return [
        f"In {universes} universes the model z-scores the outcome {quoted} as well as the "
        "predictors, because the decision rule reads a standardised coefficient: those estimates "
        "are in standard deviations of the outcome per standard deviation of the exposure, even "
        "where an option's description names the raw outcome."
    ]
