from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field

from borges.analysis.models import AnalysisPlan, AnalysisResult, Option, Step
from borges.analysis.reference_writer import write_reference
from borges.garden.executor import GardenExecutor
from borges.garden.executor_alone import run_on_root
from borges.llm.client import LLMClient, LLMError

REL_TOL = 1e-3
ABS_TOL = 1e-6
CRITICAL_VALUE_RATIO = 1.15
FEEDBACK_CHARS = 600


def _close(x: float, y: float) -> bool:
    return math.isclose(x, y, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _critical_value_only(a: AnalysisResult, b: AnalysisResult) -> bool:
    """Both intervals around the same estimate, one stretched evenly: a t critical value on one
    side and the normal 1.96 on the other. The fertility_social held-out attempts (9 October
    2026) gave the published cell as +1.2425 [+0.5443, +1.9408] and as +1.2425 [+0.5471,
    +1.9380], p and n equal, and counted it as a disagreement; t on 9 or more degrees of
    freedom is within CRITICAL_VALUE_RATIO of 1.96."""
    halves = (
        (a.estimate - a.ci_low, b.estimate - b.ci_low),
        (a.ci_high - a.estimate, b.ci_high - b.estimate),
    )
    if any(x <= 0 or y <= 0 for x, y in halves):
        return False
    low, high = (x / y for x, y in halves)
    ratio = max(low, 1 / low)
    return math.isclose(low, high, rel_tol=REL_TOL) and ratio <= CRITICAL_VALUE_RATIO


def same_result(a: AnalysisResult, b: AnalysisResult) -> bool:
    if a.n != b.n or not _close(a.estimate, b.estimate):
        return False
    bounds = _close(a.ci_low, b.ci_low) and _close(a.ci_high, b.ci_high)
    return bounds or _critical_value_only(a, b)


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
    llm: LLMClient,
    executor: GardenExecutor,
    plan: AnalysisPlan,
    attempt: int,
    fits: dict[str, dict[str, object]] | None = None,
) -> tuple[AnalysisResult | None, str]:
    """Write and run one implementation; a failed run is shown to the writer once. What the
    model fitted is kept in `fits`, by code."""
    feedback: str | None = None
    for _ in range(2):
        try:
            code = await write_reference(llm, plan, attempt, feedback)
        except LLMError as exc:
            return None, str(exc)
        fit: dict[str, object] = {}
        result, error = await run_on_root(executor, _step(plan, attempt, code), fit)
        if result is not None:
            if fits is not None:
                fits[code] = fit
            return result, code
        feedback = (error or "it failed")[:FEEDBACK_CHARS]
    return None, feedback or ""


@dataclass
class References:
    results: list[tuple[AnalysisResult, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    fits: dict[str, dict[str, object]] = field(default_factory=dict)

    @property
    def agreed(self) -> tuple[AnalysisResult, str] | None:
        for i, (result, code) in enumerate(self.results):
            if any(same_result(result, other) for other, _ in self.results[i + 1 :]):
                return result, code
        return None


async def agreed_reference(
    llm: LLMClient, executor: GardenExecutor | None, plan: AnalysisPlan
) -> References:
    """Two implementations, and a third when they disagree or one fails."""
    assert executor is not None
    found = References()

    def keep(outcome: tuple[AnalysisResult | None, str]) -> None:
        result, text = outcome
        if result is None:
            found.errors.append(text)
        else:
            found.results.append((result, text))

    for outcome in await asyncio.gather(
        reference_result(llm, executor, plan, 1, found.fits),
        reference_result(llm, executor, plan, 2, found.fits),
    ):
        keep(outcome)
    if found.agreed is None:
        keep(await reference_result(llm, executor, plan, 3, found.fits))
    return found
