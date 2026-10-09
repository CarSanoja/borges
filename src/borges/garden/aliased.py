from __future__ import annotations

import re

from borges.analysis.model_spec.render_alias import ALIAS_NOTE, REBUILT_NOTE, TANGLED_NOTE
from borges.analysis.models import StepTrace
from borges.garden.models import Garden

REPEAT = re.compile(r"(.+)_repeat\d+")


def _base(name: str) -> str:
    """The template renames a column the design holds twice to name_repeat1 (bank at 1698258
    showed contact_missing_repeat1 in a caveat); the reader sees the column's own name."""
    found = REPEAT.fullmatch(name)
    return found.group(1) if found else name


def _repeated(trace: StepTrace, name: str) -> bool:
    names = (trace.design or {}).get("names")
    if not isinstance(names, list):
        return False
    return names.count(name) >= 2 or (_base(name) != name and _base(name) in names)


def aliased_covariates(garden: Garden, repeated: bool) -> tuple[int, list[str]]:
    names: set[str] = set()
    universes = 0
    for universe in garden.universes.values():
        dropped = [
            name
            for trace in universe.traces
            if trace.note.startswith(ALIAS_NOTE)
            for name in trace.note[len(ALIAS_NOTE) :].split(";")[0].split(", ")
            if name and _repeated(trace, name) == repeated
        ]
        if dropped:
            universes += 1
            names.update(_base(name) for name in dropped)
    return universes, sorted(names)


def aliased_caveats(garden: Garden) -> list[str]:
    caveats = []
    universes, names = aliased_covariates(garden, repeated=True)
    if universes:
        caveats.append(
            f"In {universes} universes the model put {', '.join(names)} in its design twice and "
            "dropped the second copy, as R's lm does: each is still adjusted for once, so the "
            "exposure's estimate is the same."
        )
    universes, names = aliased_covariates(garden, repeated=False)
    if universes:
        caveats.append(
            f"In {universes} universes the model dropped covariates that are exact linear "
            f"combinations of earlier columns ({', '.join(names)}), as R's lm does: the column "
            "space is unchanged, so the exposure's estimate is the same as with them."
        )
    return caveats


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


def rebuilt_caveats(garden: Garden) -> list[str]:
    names: set[str] = set()
    universes = 0
    for universe in garden.universes.values():
        left = [
            name
            for trace in universe.traces
            if trace.note.startswith(REBUILT_NOTE)
            for name in trace.note[len(REBUILT_NOTE) :].split(";")[0].split(", ")
            if name
        ]
        if left:
            universes += 1
            names.update(left)
    if not universes:
        return []
    return [
        f"In {universes} universes the model left out {', '.join(sorted(names))}: by itself it "
        "rebuilds the exposure (as month dummies do for an exposure that starts at a date), so "
        "the exposure's effect cannot be separated from it and those universes are not adjusted "
        "for it."
    ]
