"""Persona sampling: independent model analysts, each running only the analysis it would choose.

This is the baseline Borges is compared against in evidence/head-to-head.md. Every analyst is
the planner model with a persona in its system message; it plans as Borges's planner does, but
only its own default path is coded (by the same coder, guard and smoke repair Borges uses) and
executed. Nothing forks, no judge scores the options, no adversary proposes any and no search
looks for a flip.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from borges.analysis.coder import code_plan
from borges.analysis.models import AnalysisPlan, DatasetProfile, DecisionRule
from borges.analysis.planner import plan_analysis
from borges.analysis.smoke_types import SmokeConfig
from borges.evaluation.grid_run import run_grid
from borges.llm.client import LLMClient, LLMResponse, Role, UsageTotals
from borges.sandbox.backend import BranchBackend

PERSONAS = (
    "a psychologist working in the field the question comes from",
    "an economist",
    "a biostatistician",
    "a methodologist who worries about small samples and flexible analyses",
    "a sociologist",
    "a survey researcher who cleans self-reported online data",
    "a Bayesian statistician asked for a frequentist answer",
    "an epidemiologist",
    "a domain expert who knows how this field measures its constructs",
    "a data scientist with no background in the field",
    "a graduate student running the first analysis of their thesis",
    "a journal reviewer re-analysing the data to check a paper",
)
PERSONA_NOTE = (
    "You are {persona}. Plan the analysis you yourself would run and report. The default "
    "option of every step is your own choice for that step; you may list alternatives, but "
    "only your defaults will be run.\n\n"
)


@dataclass
class PersonaLLM:
    inner: LLMClient
    persona: str
    index: int
    totals: UsageTotals = field(init=False)

    def __post_init__(self) -> None:
        self.totals = self.inner.totals

    async def complete(
        self,
        role: Role,
        messages: list[dict[str, str]],
        *,
        key: str,
        schema: type[BaseModel] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> LLMResponse:
        if role == Role.PLANNER:
            messages = with_persona(messages, self.persona)
            key = f"{key}:persona{self.index}"
        return await self.inner.complete(
            role, messages, key=key, schema=schema, max_tokens=max_tokens, temperature=temperature
        )


def with_persona(messages: list[dict[str, str]], persona: str) -> list[dict[str, str]]:
    note = PERSONA_NOTE.format(persona=persona)
    if messages and messages[0]["role"] == "system":
        return [{**messages[0], "content": note + messages[0]["content"]}, *messages[1:]]
    return [{"role": "system", "content": note}, *messages]


def default_path(plan: AnalysisPlan) -> AnalysisPlan:
    single = plan.model_copy(deep=True)
    for step in single.steps:
        step.options = [step.default]
    return single


async def persona_plan(
    llm: LLMClient, profile: DatasetProfile, question: str, rule: DecisionRule, index: int
) -> AnalysisPlan:
    persona = PERSONAS[index % len(PERSONAS)]
    plan = await plan_analysis(PersonaLLM(llm, persona, index), profile, question, rule)
    return default_path(plan)


async def run_persona(
    llm: LLMClient, backend: BranchBackend, plan: AnalysisPlan, data: bytes, timeout_s: float
) -> dict[str, Any]:
    smoke = SmokeConfig(
        backend,
        data,
        timeout_s=timeout_s,
        result_scale=plan.result_scale,
        metric=plan.decision_rule.metric,
    )
    coded = await code_plan(llm, plan, smoke=smoke)
    replaced = [s.id for s in coded.steps if s.default.id != plan.step(s.id).default.id]
    run = await run_grid(backend, coded, data, [coded.default_choices()], concurrency=1)
    [universe] = run.garden.universes.values()
    result = universe.result
    return {
        "status": universe.status,
        "verdict": universe.verdict,
        "estimate": result.estimate if result else None,
        "ci": [result.ci_low, result.ci_high] if result else None,
        "p_value": result.p_value if result else None,
        "n": result.n if result else None,
        "error": universe.error,
        "replaced_steps": replaced,
        "specs": {s.id: s.default.spec for s in coded.steps},
    }
