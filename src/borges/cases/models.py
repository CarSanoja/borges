from __future__ import annotations

from pydantic import BaseModel, Field

from borges.analysis.models import DecisionRule


class ReferenceEstimate(BaseModel):
    label: str
    estimate: float
    ci_low: float | None = None
    ci_high: float | None = None
    significant: bool | None = None


class CaseSpec(BaseModel):
    id: str
    title: str
    subtitle: str
    question: str
    decision_rule: DecisionRule
    dataset_file: str = "data.parquet"
    dataset_name: str
    max_universes: int = 40
    reference_label: str | None = None
    reference: list[ReferenceEstimate] = Field(default_factory=list)
    story: str = ""


class CaseCard(BaseModel):
    id: str
    title: str
    subtitle: str
    question: str
    decision_rule: DecisionRule
    n_rows: int
    has_recording: bool
    reference_label: str | None = None
    reference: list[ReferenceEstimate] = Field(default_factory=list)
    story: str = ""
