"""Check that the plan's default path is the user's own analysis, and re-plan when it is not.

On 7 Oct 2026 the planner was given the published fertility analysis three times. Once it
imputed missing items with another item's mean "to preserve sample size"; once it wrote "Original
user definition: single = Relationship 1, committed = 2, 3, 4" for an analysis that says single =
1 or 2, and the judge accepted that default at 0.9 because it trusted the rationale. The run then
measures the fragility of an analysis nobody brought. A second model reads the analysis and the
default specs side by side and lists what differs; the planner is asked to fix those, twice at
most, and what still differs is reported.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from pydantic import BaseModel, Field

from borges.analysis.prompts import compact_json, messages
from borges.analysis.prompts.planner import build_retry_messages
from borges.analysis.schemas import PlannerOutput
from borges.llm.client import LLMClient, LLMError, Role

FIDELITY_TOKENS = 1500
FIDELITY_RETRIES = 2
UNCHECKED = "the starting point could not be checked against your analysis"
Ask = Callable[[list[dict[str, str]], str], Awaitable[PlannerOutput]]
Broaden = Callable[[PlannerOutput, str], Awaitable[PlannerOutput]]
SYSTEM = """You check that the default path of an analysis plan implements the user's own \
analysis exactly. The default path is the default option of every step, run in order.

List every part of the user's analysis that the default path implements differently (a \
different set of category codes, window, cut-off, formula, date arithmetic, exclusion, model or \
standard error) or does not implement at all, and every default that adds something the analysis \
does not say (an imputation, an exclusion, a covariate, a transformation). Compare the specs, not \
the labels or rationales: a rationale that claims to follow the user is not evidence. Decisions \
the analysis leaves open are not mismatches. Return an empty list when the defaults implement the \
analysis exactly."""


class Mismatch(BaseModel):
    step_id: str
    analysis_part: str = Field(description="the words of the user's analysis at stake")
    default_spec: str = Field(description="the part of the default spec that differs")
    problem: str


class FidelityOutput(BaseModel):
    mismatches: list[Mismatch] = Field(default_factory=list)


def build_messages(out: PlannerOutput, analysis: str) -> list[dict[str, str]]:
    defaults = [
        {"step_id": step.id, "title": step.title, "default_spec": option.spec}
        for step in out.steps
        for option in step.options
        if option.is_default
    ]
    user = f"User's analysis: {analysis.strip()}\nDefault path: {compact_json(defaults)}"
    return messages(SYSTEM, user)


async def fidelity_mismatches(
    llm: LLMClient, out: PlannerOutput, analysis: str, key: str
) -> list[Mismatch]:
    response = await llm.complete(
        Role.JUDGE,
        build_messages(out, analysis),
        key=key,
        schema=FidelityOutput,
        max_tokens=FIDELITY_TOKENS,
    )
    return FidelityOutput.model_validate(response.parsed).mismatches


def as_problems(mismatches: list[Mismatch]) -> list[str]:
    return [
        f"The default option of {m.step_id} does not implement the user's analysis: {m.problem} "
        f"(the analysis says {m.analysis_part!r}; the default says {m.default_spec!r}). Make the "
        "default implement the analysis exactly and keep any other version as an alternative."
        for m in mismatches
    ]


def as_caveats(mismatches: list[Mismatch]) -> list[str]:
    return [
        f"{m.step_id}: the analysis says {m.analysis_part!r}, the starting point does "
        f"{m.default_spec!r} ({m.problem})"
        for m in mismatches
    ]


async def faithful_plan(
    llm: LLMClient,
    base: list[dict[str, str]],
    out: PlannerOutput,
    analysis: str,
    ask: Ask,
    broaden: Broaden,
) -> tuple[PlannerOutput, list[str]]:
    """Re-plan until the defaults implement the analysis; return the plan and what still differs."""
    for attempt in range(1, FIDELITY_RETRIES + 2):
        try:
            mismatches = await fidelity_mismatches(llm, out, analysis, f"fidelity:{attempt}")
        except LLMError as exc:
            return out, [f"{UNCHECKED} ({exc})"]
        if not mismatches or attempt > FIDELITY_RETRIES:
            return out, as_caveats(mismatches)
        prefix = f"planner:fidelity{attempt}"
        try:
            fixed = await ask(build_retry_messages(base, out, as_problems(mismatches)), prefix)
        except LLMError:
            return out, as_caveats(mismatches)
        out = await broaden(fixed, prefix)
    return out, []
