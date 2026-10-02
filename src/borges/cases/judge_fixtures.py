from __future__ import annotations

from borges.analysis.schemas import JudgeOutput, PlannerOutput


def planner_judge_outputs(
    planner: PlannerOutput, verdicts: dict[str, tuple[float, str]]
) -> dict[str, JudgeOutput]:
    """One accepting judgement per non-default planner option; a missing verdict is an error."""
    outputs: dict[str, JudgeOutput] = {}
    for step in planner.steps:
        for option in step.options:
            if option.is_default:
                continue
            key = f"{step.id}.{option.id}"
            defensibility, reason = verdicts[key]
            outputs[key] = JudgeOutput(
                defensibility=defensibility, accepted=True, reason=reason, source=option.source
            )
    return outputs
