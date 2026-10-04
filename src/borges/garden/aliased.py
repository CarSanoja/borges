from __future__ import annotations

from borges.analysis.model_spec.render_design import ALIAS_NOTE, TANGLED_NOTE
from borges.garden.models import Garden


def aliased_covariates(garden: Garden) -> tuple[int, list[str]]:
    names: set[str] = set()
    universes = 0
    for universe in garden.universes.values():
        dropped = [
            name
            for trace in universe.traces
            if trace.note.startswith(ALIAS_NOTE)
            for name in trace.note[len(ALIAS_NOTE) :].split(";")[0].split(", ")
            if name
        ]
        if dropped:
            universes += 1
            names.update(dropped)
    return universes, sorted(names)


def aliased_caveats(garden: Garden) -> list[str]:
    universes, names = aliased_covariates(garden)
    if not universes:
        return []
    return [
        f"In {universes} universes the model dropped covariates that are exact linear "
        f"combinations of earlier columns ({', '.join(names)}), as R's lm does: the column space "
        "is unchanged, so the exposure's estimate is the same as with them."
    ]


def tangled_covariates(garden: Garden) -> tuple[int, list[str]]:
    names: set[str] = set()
    universes = 0
    for universe in garden.universes.values():
        dropped = [
            name
            for trace in universe.traces
            if TANGLED_NOTE in trace.note
            for name in trace.note.split(TANGLED_NOTE, 1)[1].split(";")[0].split(", ")
            if name
        ]
        if dropped:
            universes += 1
            names.update(dropped)
    return universes, sorted(names)


def tangled_caveats(garden: Garden) -> list[str]:
    universes, names = tangled_covariates(garden)
    if not universes:
        return []
    return [
        f"In {universes} universes the covariates {', '.join(names)} were also dropped: together "
        "with an aliased covariate they rebuild the exposure, and adjusting for the parts of the "
        "exposure would change what its coefficient measures."
    ]
