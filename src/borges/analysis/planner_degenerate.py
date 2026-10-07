"""Plans that cannot run at all, told apart from plans that are merely thin.

On 7 Oct (UTC) five fresh fertility plans from Nemotron Ultra all estimated "the mean of Rel1",
wrote pandas code instead of describing each option, loaded data.csv and had no model step,
while five from Super all planned the interaction the question asks for. The retries kept the
shape of the first answer, and fert8 then ran a "load" step until it failed. A plan with no
model step, or one that loads files, is drawn again from scratch instead.
"""

from __future__ import annotations

import re

from borges.analysis.schemas import PlannedStep

LOADS_FILES = re.compile(r"\bread_(?:csv|parquet|excel|json|table|feather|stata|sas)\b|\bopen\(")
FRESH_TEMPERATURE = 0.6


def loading_options(steps: list[PlannedStep]) -> list[str]:
    return [f"{s.id}.{o.id}" for s in steps for o in s.options if LOADS_FILES.search(o.spec)]


def loading_shortfall(steps: list[PlannedStep]) -> str | None:
    found = loading_options(steps)
    if not found:
        return None
    return (
        "These options load a file, but the data already arrives in df and no step reads files: "
        f"{', '.join(found)}. Remove them, and describe each option in words (what it does to df "
        "or ctx) rather than as code."
    )


def is_degenerate(steps: list[PlannedStep]) -> bool:
    return not any(s.kind == "model" for s in steps) or bool(loading_options(steps))


DEGENERATE = (
    "planner: even a fresh plan has no model step or loads files, so the question cannot be "
    "analysed as planned"
)
