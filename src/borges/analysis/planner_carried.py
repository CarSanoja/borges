"""A value one step computes and a later step reads is passed on as a column.

fertility_vote on 7 October, runs 34 and 35: the first step, a filter, computed cycle_day in its
spec to keep the fertility windows and declared no products; the later steps read cycle_day. The
coders were told it was not available, so one wrote the indicator as missing when the column was
absent and the other computed it again and lost the two hand-set days. When a filter's default
spec assigns a name (name = ...) that a later step's spec reads, and neither the data nor any step
in between produces it, the name is added to what the filter produces, so its coder is told to
write it and the later coders see it. Transform and feature steps must already declare what they
produce, and their specs use names as notation ("fem = masfem" in a recorded plan whose code
writes fem_x), so they are left as planned.
"""

from __future__ import annotations

import re

from borges.analysis.models import DatasetProfile
from borges.analysis.schemas import PlannedStep

ASSIGNED = re.compile(r"(?<![\w.'\"])([A-Za-z_]\w*)\s*=(?!=)")
FRAME_NAMES = frozenset({"df", "data", "frame", "out", "ctx", "mask", "result", "self"})


def _mention(name: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w.]){re.escape(name)}(?!\w)")


def _default_spec(step: PlannedStep) -> str:
    return next((o.spec for o in step.options if o.is_default), step.options[0].spec)


def _read_later(name: str, steps: list[PlannedStep]) -> bool:
    for later in steps:
        if name in later.produces:
            return False
        specs = [o.spec for o in later.options]
        if any(_mention(name).search(spec) for spec in specs):
            return not any(name in ASSIGNED.findall(spec) for spec in specs)
    return False


def carry_computed(steps: list[PlannedStep], profile: DatasetProfile) -> list[PlannedStep]:
    columns = {c.name for c in profile.columns}
    produced = set(columns)
    carried: list[PlannedStep] = []
    for index, step in enumerate(steps):
        added: list[str] = []
        if step.kind == "filter":
            for name in dict.fromkeys(ASSIGNED.findall(_default_spec(step))):
                if (
                    name in produced
                    or name in step.produces
                    or name in FRAME_NAMES
                    or len(name) < 2
                ):
                    continue
                if _read_later(name, steps[index + 1 :]):
                    added.append(name)
        if added:
            step = step.model_copy(update={"produces": [*step.produces, *added]})
        produced |= set(step.produces)
        carried.append(step)
    return carried
