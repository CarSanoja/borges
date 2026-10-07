"""A second implementation of the user's analysis, written as one script by another model.

fertility_vote on 7 October: three runs of the published vote analysis gave three starting
points. One dropped the two participants whose day the authors set by hand and coded fertility
as -1/+1, halving the estimate; one kept cycle days 15 and 16 as low fertility; one was exact. The
plan's specs were right each time and the code was not, so a check of the specs saw nothing. Asked
for the whole analysis in one script, Super wrote the exact published cell in 4 of 5 attempts and
a syntax error in the fifth, never a wrong number; the coder model got 0 of 5. Two independent
results are compared with the step-by-step one in `runs/baseline_confirm.py`.
"""

from __future__ import annotations

from pydantic import BaseModel

from borges.analysis.code_guard import check_code
from borges.analysis.coder_checks import option_violations
from borges.analysis.coder_normalise import strip_trailing_closer
from borges.analysis.models import AnalysisPlan, AnalysisResult, StepTrace
from borges.analysis.prompts.reference import build_fix_messages, build_write_messages
from borges.analysis.schemas import CoderOutput
from borges.llm.client import LLMClient, LLMError, Role

REFERENCE_TOKENS = 4000
FIX_TOKENS = 6000


class Fix(BaseModel):
    step_id: str
    option_id: str
    problem: str
    code: str
    spec: str | None = None


class FixOutput(BaseModel):
    fixes: list[Fix]


async def write_reference(
    llm: LLMClient, plan: AnalysisPlan, attempt: int, feedback: str | None = None
) -> str:
    for round_ in range(2):
        response = await llm.complete(
            Role.REPAIRER,
            build_write_messages(plan, attempt, feedback),
            key=f"reference:{attempt}:{round_}",
            schema=CoderOutput,
            max_tokens=REFERENCE_TOKENS,
            temperature=0.7,
        )
        code, _ = strip_trailing_closer(CoderOutput.model_validate(response.parsed).code)
        violations = check_code(code, "model", whole=True)
        if not violations:
            return code
        feedback = "the code was refused: " + "; ".join(violations)[:1200]
    raise LLMError(f"the independent implementation was refused: {feedback}")


async def propose_fixes(
    llm: LLMClient,
    plan: AnalysisPlan,
    traces: list[StepTrace],
    ours: AnalysisResult,
    theirs: AnalysisResult,
    reference_code: str,
) -> list[Fix]:
    response = await llm.complete(
        Role.REPAIRER,
        build_fix_messages(plan, traces, ours, theirs, reference_code),
        key="reference:fix",
        schema=FixOutput,
        max_tokens=FIX_TOKENS,
    )
    fixes = []
    for fix in FixOutput.model_validate(response.parsed).fixes:
        step = next((s for s in plan.steps if s.id == fix.step_id), None)
        option = next((o for o in step.options if o.id == fix.option_id), None) if step else None
        if step is None or option is None:
            continue
        code, _ = strip_trailing_closer(fix.code)
        checked = option.model_copy(update={"spec": fix.spec}) if fix.spec else option
        if not option_violations(code, plan, step, checked):
            fixes.append(fix.model_copy(update={"code": code}))
    return fixes
