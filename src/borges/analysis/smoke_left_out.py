from __future__ import annotations

from borges.analysis.models import Option, Step
from borges.analysis.smoke_core import execute
from borges.analysis.smoke_types import Outcome, SmokeConfig
from borges.sandbox.backend import Checkpoint

LEFT_OUT_ID = "left_out"
IDENTITY = "def apply(df, ctx):\n    return df\n"
REASON_CHARS = 300
NOTE = (
    "The decision '{title}' was left out of the analysis: none of its options could be run "
    "({tried}; last error: {reason}). The data passes through that step unchanged, so the "
    "result does not reflect that decision."
)


def identity_option() -> Option:
    return Option(
        id=LEFT_OUT_ID,
        label="Left out",
        rationale="No option of this step could be run.",
        spec="Return the input DataFrame unchanged.",
        is_default=True,
        code=IDENTITY,
    )


async def leave_out(
    config: SmokeConfig, step: Step, parent: Checkpoint, failed: list[Outcome]
) -> Outcome | None:
    """Replace a data step none of whose options runs by a pass-through, and say so."""
    option = identity_option()
    blank = step.model_copy(update={"options": [option], "produces": []})
    checkpoint, error, effects, _ = await execute(config, parent, blank, option)
    if error is not None or checkpoint is None:
        return None
    tried = ", ".join(o.option.label for o in failed) or "none was coded"
    reason = next((o.error for o in reversed(failed) if o.error), "not coded")
    step.options = [option]
    step.produces = []
    config.state.notes.append(
        NOTE.format(title=step.title, tried=tried, reason=str(reason)[:REASON_CHARS])
    )
    if config.on_smoke is not None:
        await config.on_smoke(step.id, option.id, "passed", 1, "the step was left out", [])
    return Outcome(option, "passed", 1, None, checkpoint, [], effects)
