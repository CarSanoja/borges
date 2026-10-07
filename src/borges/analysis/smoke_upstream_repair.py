"""A constant model input caused further up than the step before the model, repaired there.

fertility_vote on 7 October: the default filter labelled every row "low", marked the high window
"high" and kept the rows not labelled "low", so only the high-fertility women reached the model.
The model refused a constant exposure, and the re-plan went to the step just before the model,
which coded relationship status and was never the problem. The filter's spec was right and its
code was wrong, so the code is repaired, not the plan. Each earlier default that dropped rows is
asked first, nearest first, then each that writes the constant column; the first repair that
passes its re-review and lets the model's default run is kept, and the smoke run starts again
from that step so every later step sees the repaired data.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from borges.analysis.models import CodingSummary, Option, Step
from borges.analysis.rebuild_names import rebuilt_names
from borges.analysis.smoke_types import Outcome, Repair, SmokeConfig
from borges.analysis.smoke_upstream import _repaired, _short
from borges.analysis.smoke_upstream_replan import FAULT_CHARS, input_fault

EXPOSURE = re.compile(r"the exposure (\S+) has the same value in every row")
MESSAGE = (
    "With this option as the default, the model step '{title}' later fails on the sample: "
    "{error}\nThis option keeps {after} of the {before} rows it receives. Check that the code "
    "keeps exactly the rows its spec keeps and builds each column the way the spec says; fix the "
    "code, and do not change what the spec does."
)
NOTE = (
    "The model step '{title}' failed on the sample because its input was constant ({error}); "
    "the code of the default of '{earlier}' was repaired against its unchanged spec, and the "
    "steps from there were smoke-tested again."
)


@dataclass
class Mark:
    """What a step looked like before its first smoke round, to start again from it."""

    notes: int
    summary: CodingSummary | None
    options: list[Option]


def mark(config: SmokeConfig, summary: CodingSummary | None, step: Step) -> Mark:
    copied = summary.model_copy() if summary is not None else None
    return Mark(len(config.state.notes), copied, [o.model_copy(deep=True) for o in step.options])


def _rows(outcome: Outcome) -> tuple[int | None, int | None]:
    effects = outcome.effects or {}
    return effects.get("rows_before"), effects.get("rows_after")


def _candidates(
    config: SmokeConfig, steps: Sequence[Step], index: int, column: str | None
) -> list[int]:
    dropped: list[int] = []
    writes: list[int] = []
    for j in range(index - 1, -1, -1):
        default = config.state.defaults.get(steps[j].id)
        if default is None or default.checkpoint is None or default.option.code is None:
            continue
        before, after = _rows(default)
        if before is not None and after is not None and after < before:
            dropped.append(j)
        elif column is not None and column in rebuilt_names(default.option.code):
            writes.append(j)
    return [*dropped, *writes]


async def repair_upstream_default(
    config: SmokeConfig, repair: Repair, steps: Sequence[Step], index: int, outcomes: list[Outcome]
) -> tuple[int, str] | None:
    fault = input_fault(outcomes)
    if fault is None:
        return None
    model = steps[index]
    found = EXPOSURE.search(fault)
    for j in _candidates(config, steps, index, found.group(1) if found else None):
        earlier, default = steps[j], config.state.defaults[steps[j].id]
        before, after = _rows(default)
        message = MESSAGE.format(
            title=model.title,
            error=fault[:FAULT_CHARS],
            before="?" if before is None else before,
            after="?" if after is None else after,
        )
        between = steps[j + 1 : index]
        fresh = await _repaired(
            config, repair, earlier, model, default, fault, between, message=message
        )
        if fresh is None:
            continue
        earlier.options = [fresh.option if o.id == fresh.option.id else o for o in earlier.options]
        return j, fault
    return None


def restart(
    config: SmokeConfig,
    summary: CodingSummary | None,
    marks: dict[str, Mark],
    steps: Sequence[Step],
    span: tuple[int, int],
    fault: str,
) -> None:
    """Put the state back as it was before step j first ran, keeping its repaired default, and
    give the later steps back the options their smoke rounds on the bad data dropped."""
    j, index = span
    kept = marks[steps[j].id]
    del config.state.notes[kept.notes :]
    if summary is not None and kept.summary is not None:
        for name in CodingSummary.model_fields:
            setattr(summary, name, getattr(kept.summary, name))
        summary.repaired_after_smoke += 1
    for later in steps[j + 1 : index + 1]:
        later.options = [o.model_copy(deep=True) for o in marks[later.id].options]
    config.state.notes.append(
        NOTE.format(title=steps[index].title, error=_short(fault), earlier=steps[j].title)
    )
