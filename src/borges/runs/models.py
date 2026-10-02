from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from borges.analysis.models import AnalysisPlan, DecisionRule, Option, Step, StepTrace
from borges.garden.models import Flip, Garden, Report, Universe
from borges.runs.events import StageName

RunStatus = Literal["running", "completed", "failed"]


class RunRequest(BaseModel):
    case_id: str | None = None
    upload_id: str | None = None
    question: str | None = Field(default=None, max_length=1000)
    decision_rule: DecisionRule | None = None
    llm: Literal["nebius", "scripted", "local"] | None = None
    backend: Literal["local", "contree"] | None = None
    max_universes: int | None = Field(default=None, ge=1, le=200)


class RunCreated(BaseModel):
    run_id: str


class CheckpointNode(BaseModel):
    checkpoint_id: str
    parent_id: str | None
    step_id: str | None
    option_id: str | None
    depth: int


class UsageSnapshot(BaseModel):
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    llm_calls: int = 0
    cached_calls: int = 0
    checkpoints: int = 0
    universes: int = 0


class RunSnapshot(BaseModel):
    run_id: str
    status: RunStatus = "running"
    case_id: str | None = None
    title: str = ""
    question: str = ""
    decision_rule: DecisionRule | None = None
    llm: Literal["nebius", "scripted", "local"] | None = None
    backend: str | None = None
    stages: dict[StageName, Literal["started", "done"]] = Field(default_factory=dict)
    plan: AnalysisPlan | None = None
    checkpoints: list[CheckpointNode] = Field(default_factory=list)
    garden: Garden = Field(default_factory=Garden)
    flip: Flip | None = None
    report: Report | None = None
    usage: UsageSnapshot = Field(default_factory=UsageSnapshot)
    error: str | None = None
    last_seq: int = 0


class RunSummary(BaseModel):
    run_id: str
    case_id: str | None
    title: str
    status: RunStatus
    created_at: float
    llm: str
    backend: str
    cost_usd: float
    n_universes: int
    verdict: str | None
    flipped_verdict: str | None


class UniverseStepDetail(BaseModel):
    step: Step
    option: Option
    trace: StepTrace | None
    changed: bool
    checkpoint_id: str | None


class UniverseDetail(BaseModel):
    universe: Universe
    steps: list[UniverseStepDetail]
    reproduce_command: str
