from __future__ import annotations

from pydantic import BaseModel, Field

from borges.analysis.models import StepKind


class PlannedOption(BaseModel):
    id: str
    label: str
    rationale: str
    spec: str
    is_default: bool = False
    source: str | None = None


class PlannedStep(BaseModel):
    id: str
    title: str
    kind: StepKind
    description: str
    options: list[PlannedOption] = Field(min_length=1)
    produces: list[str] = Field(default_factory=list)


class PlannerOutput(BaseModel):
    estimand: str
    steps: list[PlannedStep] = Field(min_length=1)


class CoderOutput(BaseModel):
    code: str


class ProposedOption(BaseModel):
    step_id: str
    id: str
    label: str
    rationale: str
    spec: str
    source: str | None = None


class AdversaryOutput(BaseModel):
    proposals: list[ProposedOption] = Field(default_factory=list)


class JudgeOutput(BaseModel):
    defensibility: float = Field(ge=0.0, le=1.0)
    accepted: bool
    reason: str
    source: str | None = None


class NarratorOutput(BaseModel):
    narrative: str
    caveats: list[str] = Field(default_factory=list)


class ReviewVerdict(BaseModel):
    option_id: str
    faithful: bool
    changes_estimand: bool = False
    problem: str = ""


class ReviewerOutput(BaseModel):
    verdicts: list[ReviewVerdict] = Field(default_factory=list)
