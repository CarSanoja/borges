from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from borges.analysis.models import AnalysisResult, CodingSummary, StepTrace

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


class DecisionInfluence(BaseModel):
    step_id: str
    title: str
    mean_abs_delta: float
    max_abs_delta: float
    flips: int
    n_alternatives: int


class SearchSummary(BaseModel):
    levels_explored: int = 0
    max_combinations_per_level: int = 0
    universe_budget: int = 0
    universes_used: int = 0
    budget_exhausted: bool = False


class Report(BaseModel):
    question: str
    original_verdict: str
    original_result: AnalysisResult
    minimal_flip: Flip | None
    influences: list[DecisionInfluence]
    robustness: float
    n_universes: int
    n_flipped: int
    narrative: str = ""
    caveats: list[str] = Field(default_factory=list)
    n_failed: int = 0
    failed: list[str] = Field(default_factory=list)
    search: SearchSummary | None = None
    coding: CodingSummary | None = None


class Garden(BaseModel):
    baseline_id: str | None = None
    universes: dict[str, Universe] = Field(default_factory=dict)

    def add(self, universe: Universe) -> None:
        self.universes[universe.id] = universe

    @property
    def baseline(self) -> Universe | None:
        return self.universes.get(self.baseline_id) if self.baseline_id else None

    def finished(self) -> list[Universe]:
        return [u for u in self.universes.values() if u.status == "done" and u.result]
