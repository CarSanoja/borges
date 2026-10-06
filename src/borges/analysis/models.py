from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Comparator(StrEnum):
    GT = "gt"
    LT = "lt"


class DecisionRule(BaseModel):
    metric: str
    comparator: Comparator = Comparator.GT
    threshold: float = 0.0
    alpha: float = 0.05
    positive_label: str = "SHIP"
    negative_label: str = "DON'T SHIP"

    def is_positive(self, result: AnalysisResult) -> bool:
        beyond = (
            result.estimate > self.threshold
            if self.comparator is Comparator.GT
            else result.estimate < self.threshold
        )
        return beyond and result.p_value < self.alpha

    def label(self, result: AnalysisResult) -> str:
        return self.positive_label if self.is_positive(result) else self.negative_label


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    n_missing: int
    n_unique: int
    summary: dict[str, float | str] = Field(default_factory=dict)
    note: str | None = None


class RepeatedUnit(BaseModel):
    name: str
    n_units: int
    rows_per_unit: float


class DatasetProfile(BaseModel):
    name: str
    n_rows: int
    columns: list[ColumnProfile]
    sample_rows: list[dict[str, object]] = Field(default_factory=list)
    repeated_units: list[RepeatedUnit] = Field(default_factory=list)


StepKind = Literal["filter", "transform", "feature", "model"]
OptionOrigin = Literal["planner", "adversary", "pinned"]


class Option(BaseModel):
    id: str
    label: str
    rationale: str
    spec: str
    is_default: bool = False
    origin: OptionOrigin = "planner"
    source: str | None = None
    defensibility: float | None = None
    code: str | None = None
    cluster_by: str | None = None


class Step(BaseModel):
    id: str
    title: str
    kind: StepKind
    description: str
    options: list[Option]
    produces: list[str] = Field(default_factory=list)

    @property
    def is_decision(self) -> bool:
        return len(self.options) > 1

    @property
    def default(self) -> Option:
        return next((o for o in self.options if o.is_default), self.options[0])

    def option(self, option_id: str) -> Option:
        return next(o for o in self.options if o.id == option_id)


class AnalysisPlan(BaseModel):
    question: str
    estimand: str
    decision_rule: DecisionRule
    dataset: DatasetProfile
    steps: list[Step]
    result_scale: float = 1.0

    def step(self, step_id: str) -> Step:
        return next(s for s in self.steps if s.id == step_id)

    def default_choices(self) -> dict[str, str]:
        return {s.id: s.default.id for s in self.steps}

    @property
    def decision_steps(self) -> list[Step]:
        return [s for s in self.steps if s.is_decision]


class AnalysisResult(BaseModel):
    estimate: float
    ci_low: float
    ci_high: float
    p_value: float
    n: int
    metric: str = ""
    extra: dict[str, float] = Field(default_factory=dict)


class StepTrace(BaseModel):
    step_id: str
    option_id: str
    rows_before: int
    rows_after: int
    note: str = ""
    fingerprint: str | None = None
    design: dict[str, object] | None = None


class Judgement(BaseModel):
    defensibility: float = Field(ge=0.0, le=1.0)
    accepted: bool
    reason: str
    source: str | None = None


class Proposal(BaseModel):
    step_id: str
    option: Option


class CodingSummary(BaseModel):
    options: int = 0
    smoke_tested: int = 0
    repaired_after_smoke: int = 0
    failed: int = 0
    steps_reviewed: int = 0
    options_flagged: int = 0
    options_dropped_by_review: int = 0
    options_dropped_by_judge: int = 0
    options_added_after_judge: int = 0
    options_dropped_by_armor: int = 0
    options_recoded_by_output_check: int = 0
