from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from borges.analysis.models import AnalysisResult, CodingSummary, StepTrace
from borges.fleet.models import RunAgents

UniverseKind = Literal["baseline", "single", "adversary", "combination", "verification"]
UniverseStatus = Literal["pending", "running", "done", "failed"]


class Universe(BaseModel):
    id: str
    choices: dict[str, str]
    changed: list[str] = Field(default_factory=list)
    kind: UniverseKind
    status: UniverseStatus = "pending"
    result: AnalysisResult | None = None
    verdict: str | None = None
    flipped: bool | None = None
    checkpoints: list[str] = Field(default_factory=list)
    traces: list[StepTrace] = Field(default_factory=list)
    error: str | None = None
    duration_s: float = 0.0


class Change(BaseModel):
    step_id: str
    step_title: str
    from_option: str
    to_option: str
    to_label: str
    rationale: str
    source: str | None = None
    defensibility: float | None = None


class Flip(BaseModel):
    universe_id: str
    changes: list[Change]
    baseline_result: AnalysisResult
    flipped_result: AnalysisResult
    baseline_verdict: str
    flipped_verdict: str
    reproduced: bool | None = None
    reproduce_command: str | None = None
    kind: Literal["direction", "significance"] | None = None
    estimand_change: str | None = None
    contaminated: bool = False
    contamination_reason: str | None = None


class DecisionInfluence(BaseModel):
    step_id: str
    title: str
    mean_abs_delta: float
    max_abs_delta: float
    flips: int
    n_alternatives: int


class NoopOption(BaseModel):
    step_id: str
    option_id: str
    label: str
    reason: str


class DuplicateOption(NoopOption):
    kept_option_id: str
    kept_label: str
    kept_origin: str


class EstimandChange(BaseModel):
    step_id: str
    option_id: str
    label: str
    detail: str


RobustnessBasis = Literal["design_weighted", "distinct_results", "none"]


class SearchSummary(BaseModel):
    levels_explored: int = 0
    max_combinations_per_level: int = 0
    universe_budget: int = 0
    universes_used: int = 0
    budget_exhausted: bool = False
    sample_draws: int = 0


class Report(BaseModel):
    question: str
    original_verdict: str
    original_result: AnalysisResult
    minimal_flip: Flip | None
    influences: list[DecisionInfluence]
    robustness: float
    n_universes: int
    n_flipped: int
    n_distinct_results: int = 0
    robustness_basis: RobustnessBasis = "distinct_results"
    robustness_beam: float | None = None
    robustness_design: float | None = None
    robustness_design_note: str | None = None
    robustness_rating: float | None = None
    robustness_rating_reason: str | None = None
    noop_options: list[NoopOption] = Field(default_factory=list)
    duplicate_options: list[DuplicateOption] = Field(default_factory=list)
    estimand_changes: list[EstimandChange] = Field(default_factory=list)
    contaminated_flip: Flip | None = None
    narrator_input_tokens: int | None = None
    narrative: str = ""
    caveats: list[str] = Field(default_factory=list)
    n_failed: int = 0
    failed: list[str] = Field(default_factory=list)
    search: SearchSummary | None = None
    coding: CodingSummary | None = None
    agents: RunAgents | None = None


class Garden(BaseModel):
    baseline_id: str | None = None
    universes: dict[str, Universe] = Field(default_factory=dict)
    sample_ids: list[str] = Field(default_factory=list)

    def add(self, universe: Universe) -> None:
        self.universes[universe.id] = universe

    @property
    def baseline(self) -> Universe | None:
        return self.universes.get(self.baseline_id) if self.baseline_id else None

    def finished(self) -> list[Universe]:
        return [u for u in self.universes.values() if u.status == "done" and u.result]
