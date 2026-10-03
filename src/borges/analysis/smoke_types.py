from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from borges.analysis.models import Option, Step
from borges.analysis.schemas import ReviewVerdict
from borges.sandbox.backend import BranchBackend, Checkpoint

if TYPE_CHECKING:
    from borges.analysis.smoke_larger import LargerSample

OnSmoke = Callable[..., Awaitable[None]]
OnReview = Callable[[str, str, bool, bool, str, str], Awaitable[None]]
Repair = Callable[[Step, Option, str, int], Awaitable[tuple[str, str | None, str]]]
Recode = Callable[[Step, Option, list[str]], Awaitable[tuple[str, str | None, str]]]
Check = Callable[[dict[str, Any] | None], str | None]


@dataclass
class ReviewEntry:
    option: Option
    effects: dict[str, Any] | None
    result: dict[str, Any] | None


@dataclass
class ReviewResult:
    verdicts: list[ReviewVerdict]
    model: str


Reviewer = Callable[..., Awaitable[ReviewResult | None]]


@dataclass
class SmokeState:
    parents: dict[str, Checkpoint] = field(default_factory=dict)
    defaults: dict[str, Outcome] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    larger_rows: dict[tuple[str, str], int] = field(default_factory=dict)


@dataclass
class SmokeConfig:
    backend: BranchBackend
    data: bytes
    on_smoke: OnSmoke | None = None
    timeout_s: float = 60.0
    reviewer: Reviewer | None = None
    on_review: OnReview | None = None
    result_check: Callable[[dict[str, Any]], str | None] | None = None
    result_scale: float = 1.0
    larger: LargerSample | None = None
    state: SmokeState = field(default_factory=SmokeState)


@dataclass
class Outcome:
    option: Option
    status: str
    attempts: int
    error: str | None
    checkpoint: Checkpoint | None
    models: list[str]
    effects: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)
    sample_rows: int | None = None
