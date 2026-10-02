from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from borges.analysis.models import Option, Step
from borges.analysis.schemas import ReviewVerdict
from borges.sandbox.backend import BranchBackend, Checkpoint

OnSmoke = Callable[[str, str, str, int, str | None, list[str]], Awaitable[None]]
OnReview = Callable[[str, str, bool, bool, str, str], Awaitable[None]]
Repair = Callable[[Step, Option, str, int], Awaitable[tuple[str, str | None, str]]]
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


Reviewer = Callable[[Step, list[ReviewEntry]], Awaitable[ReviewResult | None]]


@dataclass
class SmokeConfig:
    backend: BranchBackend
    data: bytes
    on_smoke: OnSmoke | None = None
    timeout_s: float = 60.0
    reviewer: Reviewer | None = None
    on_review: OnReview | None = None


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
