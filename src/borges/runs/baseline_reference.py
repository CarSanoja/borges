from __future__ import annotations

import math

from borges.analysis.models import AnalysisPlan, AnalysisResult, Option, Step
from borges.analysis.reference_writer import write_reference
from borges.garden.executor import GardenExecutor
from borges.garden.executor_alone import run_on_root
from borges.llm.client import LLMClient, LLMError

REL_TOL = 1e-3
ABS_TOL = 1e-6
FEEDBACK_CHARS = 600


def same_result(a: AnalysisResult, b: AnalysisResult) -> bool:
    if a.n != b.n:
        return False
    pairs = ((a.estimate, b.estimate), (a.ci_low, b.ci_low), (a.ci_high, b.ci_high))
    return all(math.isclose(x, y, rel_tol=REL_TOL, abs_tol=ABS_TOL) for x, y in pairs)


def describe(result: AnalysisResult) -> str:
    return (
        f"{result.estimate:+.4f} [{result.ci_low:+.4f}, {result.ci_high:+.4f}], "
        f"p {result.p_value:.4g}, n {result.n}"
    )


def _step(plan: AnalysisPlan, attempt: int, code: str) -> Step:
    option = Option(
        id=f"r{attempt}",
        label="independent implementation",
        rationale="",
        spec=plan.analysis,
        is_default=True,
        code=code,
    )
    return Step(
        id="reference",
        title="Independent implementation of the analysis",
        kind="model",
        description=plan.analysis,
        options=[option],
    )


async def reference_result(
    llm: LLMClient, executor: GardenExecutor, plan: AnalysisPlan, attempt: int
) -> tuple[AnalysisResult | None, str]:
    """Write and run one implementation; a failed run is shown to the writer once."""
    feedback: str | None = None
    for _ in range(2):
        try:
            code = await write_reference(llm, plan, attempt, feedback)
        except LLMError as exc:
            return None, str(exc)
        result, error = await run_on_root(executor, _step(plan, attempt, code))
        if result is not None:
            return result, code
        feedback = (error or "it failed")[:FEEDBACK_CHARS]
    return None, feedback or ""
