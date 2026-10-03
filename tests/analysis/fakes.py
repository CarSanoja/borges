from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from borges.analysis.models import (
    AnalysisPlan,
    ColumnProfile,
    DatasetProfile,
    DecisionRule,
    Option,
    Step,
)
from borges.llm.client import LLMError, LLMResponse, Role, Usage, UsageTotals


@dataclass
class Call:
    role: Role
    messages: list[dict[str, str]]
    key: str
    schema: type[BaseModel] | None
    max_tokens: int


@dataclass
class FakeLLM:
    responses: dict[str, BaseModel | dict[str, Any]]
    calls: list[Call] = field(default_factory=list)
    declined_specs: list[str] = field(default_factory=list)
    totals: UsageTotals = field(default_factory=UsageTotals)

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
        if key.endswith(":spec") and key not in self.responses:
            self.declined_specs.append(key)
            raise LLMError(f"no scripted response for {key}")
        self.calls.append(Call(role, messages, key, schema, max_tokens))
        if key not in self.responses:
            raise LLMError(f"no scripted response for {key}")
        value = self.responses[key]
        parsed = value.model_dump() if isinstance(value, BaseModel) else value
        return LLMResponse(role=role, text="", parsed=parsed, usage=Usage(model="fake"))

    def keys(self) -> list[str]:
        return [c.key for c in self.calls]


def make_profile() -> DatasetProfile:
    return DatasetProfile(
        name="trial",
        n_rows=100,
        columns=[
            ColumnProfile(name="group", dtype="object", n_missing=0, n_unique=2),
            ColumnProfile(name="outcome", dtype="float64", n_missing=3, n_unique=90),
        ],
    )


def make_option(option_id: str, default: bool = False, code: str | None = None) -> Option:
    return Option(
        id=option_id,
        label=f"Label {option_id}",
        rationale=f"Why {option_id}",
        spec=f"Spec for {option_id} on outcome",
        is_default=default,
        code=code,
    )


def make_plan(with_code: bool = False) -> AnalysisPlan:
    def code(name: str) -> str | None:
        return f"def {name}(df, ctx):\n    return df" if with_code else None

    return AnalysisPlan(
        question="Does the treatment raise the outcome?",
        estimand="Mean difference in outcome between groups",
        decision_rule=DecisionRule(metric="mean_diff"),
        dataset=make_profile(),
        steps=[
            Step(
                id="d1",
                title="Outliers",
                kind="filter",
                description="Handle outliers",
                options=[make_option("keep", True, code("apply")), make_option("trim")],
            ),
            Step(
                id="m1",
                title="Estimator",
                kind="model",
                description="Estimate",
                options=[make_option("ols", True, code("estimate")), make_option("welch")],
            ),
        ],
    )
