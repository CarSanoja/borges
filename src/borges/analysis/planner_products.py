from __future__ import annotations

import re

from borges.analysis.models import DatasetProfile, Step
from borges.analysis.schemas import PlannedStep

PRODUCING_KINDS = ("transform", "feature")
CTX_KEYS = frozenset({"covariates", "outcome"})
QUOTED = re.compile(r"""["']([A-Za-z_]\w*)["']""")


def _mention(name: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w.]){re.escape(name)}(?!\w)")


def _named(spec: str, names: list[str]) -> set[str]:
    return {name for name in names if _mention(name).search(spec)}


def builds_elsewhere(spec: str, kept: set[str], names: list[str], columns: set[str]) -> bool:
    """True when an option's spec builds other produced names than `kept`, or a new name."""
    named = _named(spec, names)
    own = set(QUOTED.findall(spec)) - columns - set(names)
    return bool(named and not named & kept) or (not named and bool(own))


def other_names(step: Step, spec: str, columns: set[str]) -> bool:
    """True when a new option of a built step would build its result under other names."""
    names = [n for n in step.produces if n not in CTX_KEYS]
    if step.kind not in PRODUCING_KINDS or not names:
        return False
    kept = _named(step.default.spec, names)
    return bool(kept) and builds_elsewhere(spec, kept, names, columns)


def renamed_products(steps: list[PlannedStep], profile: DatasetProfile) -> dict[str, list[str]]:
    """Options that build their result under other names than the step's default does, either
    another produced name or a new name of their own: a later step reads one set of names, so
    such an option would have no effect."""
    columns = {c.name for c in profile.columns}
    found: dict[str, list[str]] = {}
    for step in steps:
        names = [n for n in step.produces if n not in CTX_KEYS]
        if step.kind not in PRODUCING_KINDS or len(step.options) < 2 or not names:
            continue
        default = next((o for o in step.options if o.is_default), step.options[0])
        kept = _named(default.spec, names)
        if not kept:
            continue
        silent = [o.id for o in step.options if builds_elsewhere(o.spec, kept, names, columns)]
        if silent:
            found[step.id] = silent
    return found


def renamed_shortfall(found: dict[str, list[str]], steps: list[PlannedStep]) -> str | None:
    if not found:
        return None
    produces = {s.id: s.produces for s in steps}
    listed = "; ".join(
        f"{step_id}: {', '.join(ids)} (the step produces {', '.join(produces[step_id])})"
        for step_id, ids in sorted(found.items())
    )
    return (
        "In these steps an option builds its result under its own column name instead of the "
        "names the step produces, so the steps after it never read that option's result and "
        f"the choice has no effect: {listed}. Every option of a step writes the same produced "
        "names with the same meaning (for example one neutral name such as 'outcome_t' for a "
        "transformed outcome), and later steps read those names."
    )


def drop_renamed(steps: list[PlannedStep], profile: DatasetProfile) -> list[PlannedStep]:
    found = renamed_products(steps, profile)
    kept: list[PlannedStep] = []
    for step in steps:
        if step.id not in found:
            kept.append(step)
            continue
        options = [o for o in step.options if o.id not in found[step.id]]
        default = next((o for o in options if o.is_default), options[0])
        named = _named(default.spec, list(step.produces))
        produces = [n for n in step.produces if n in named or n in CTX_KEYS]
        kept.append(step.model_copy(update={"options": options, "produces": produces}))
    return kept
