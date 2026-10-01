from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Universe, UniverseKind
from borges.sandbox.backend import BranchBackend, Checkpoint

EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]


def universe_id(choices: dict[str, str]) -> str:
    raise NotImplementedError


class GardenExecutor:
    def __init__(
        self,
        backend: BranchBackend,
        plan: AnalysisPlan,
        data: bytes,
        emit: EmitFn | None = None,
        concurrency: int = 6,
        reuse_prefixes: bool = True,
    ) -> None:
        self.backend = backend
        self.plan = plan
        self.data = data
        self.emit = emit
        self.concurrency = concurrency
        self.reuse_prefixes = reuse_prefixes
        self.baseline_verdict: str | None = None
        self.root: Checkpoint | None = None

    @property
    def checkpoints_created(self) -> int:
        raise NotImplementedError

    async def setup(self) -> Checkpoint:
        raise NotImplementedError

    async def run_universe(self, choices: dict[str, str], kind: UniverseKind) -> Universe:
        raise NotImplementedError
