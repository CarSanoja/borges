from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from borges.analysis.models import DecisionRule
from borges.cases.recording_stamp import RecordingStamp


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
    live_only: bool = False
    owner: str = "borges-core"
    provenance: str = ""
    column_notes: dict[str, str] = Field(default_factory=dict)


class ResultBrief(BaseModel):
    estimate: float
    ci_low: float
    ci_high: float
    p_value: float
    n: int


class LiveRecordingSummary(BaseModel):
    recorded_at: str
    models: dict[str, str] = Field(default_factory=dict)
    llm_calls: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    verdict: str | None = None
    flipped_verdict: str | None = None
    flip_kind: Literal["direction", "significance"] | None = None
    universes: int
    baseline: ResultBrief | None = None
    flipped: ResultBrief | None = None
    flip_changes: list[str] = Field(default_factory=list)
    contaminated: bool = False
    estimand_change: str | None = None


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
    live_only: bool = False
    provenance: str = ""
    traced_sources: list[str] = Field(default_factory=list)
    live_recording: LiveRecordingSummary | None = None
    recording_meta: dict[str, RecordingStamp] = Field(default_factory=dict)
