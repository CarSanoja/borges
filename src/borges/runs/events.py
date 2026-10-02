from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

EventType = Literal[
    "run.started",
    "stage",
    "plan.ready",
    "option.coded",
    "option.smoke",
    "option.reviewed",
    "option.proposed",
    "option.judged",
    "checkpoint.created",
    "universe.started",
    "universe.finished",
    "flip.found",
    "flip.verified",
    "usage",
    "report.ready",
    "run.finished",
    "run.failed",
]

StageName = Literal[
    "profiling",
    "planning",
    "coding",
    "baseline",
    "single_flips",
    "adversary",
    "combination_flips",
    "verifying",
    "narrating",
]


class Event(BaseModel):
    seq: int
    ts: float
    run_id: str
    type: EventType
    data: dict[str, Any] = Field(default_factory=dict)


class RunStartedData(BaseModel):
    case_id: str | None
    title: str
    question: str
    decision_rule: dict[str, Any]
    mode: Literal["live", "replay"]
    llm: Literal["nebius", "scripted", "local"]
    backend: str
    models: dict[str, str]
    max_universes: int
    trace_id: str | None = None


class StageData(BaseModel):
    name: StageName
    status: Literal["started", "done"]
    detail: str = ""


class OptionCodedData(BaseModel):
    step_id: str
    option_id: str
    ok: bool
    attempts: int
    error: str | None = None
    models: list[str] = Field(default_factory=list)


class OptionSmokeData(BaseModel):
    step_id: str
    option_id: str
    status: Literal["passed", "repaired", "failed"]
    attempts: int
    error: str | None = None
    models: list[str] = Field(default_factory=list)
    sample_rows: int | None = None


class OptionReviewedData(BaseModel):
    step_id: str
    option_id: str
    faithful: bool
    changes_estimand: bool
    problem: str = ""
    model: str = ""


class OptionJudgedData(BaseModel):
    step_id: str
    option_id: str
    defensibility: float
    accepted: bool
    reason: str
    origin: Literal["planner", "adversary"] = "adversary"


class CheckpointCreatedData(BaseModel):
    checkpoint_id: str
    parent_id: str | None
    step_id: str | None
    option_id: str | None
    depth: int
    duration_s: float = 0.0


class UsageData(BaseModel):
    tokens_in: int
    tokens_out: int
    cost_usd: float
    llm_calls: int
    cached_calls: int
    checkpoints: int
    universes: int


class RunFinishedData(BaseModel):
    status: Literal["completed", "failed"]
    elapsed_s: float


class RunFailedData(BaseModel):
    error: str
