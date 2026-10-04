from __future__ import annotations

import asyncio
import io
import re
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import pandas as pd

from borges.analysis import harness
from borges.analysis.models import Option, Step
from borges.sandbox.backend import Checkpoint

if TYPE_CHECKING:
    from borges.analysis.smoke_types import Outcome, SmokeConfig

LARGE_MAX_ROWS = 20000
LARGE_SEED = 7
SINGULAR_PATTERN = re.compile(
    r"singular|collinear|perfect\s*separation|perfectseparation|linalgerror", re.IGNORECASE
)

EMPTY_PATTERN = re.compile(
    r"zero-size array|\bempty\b|no (?:rows|observations)|\b0 (?:rows|observations)\b",
    re.IGNORECASE,
)

Executed = tuple[Checkpoint | None, str | None, dict[str, Any] | None, dict[str, Any] | None]
Run = Callable[["SmokeConfig", Checkpoint, Step, Option], Awaitable[Executed]]


def is_singular_error(error: str | None) -> bool:
    return bool(error) and SINGULAR_PATTERN.search(error or "") is not None


def is_sample_artefact(error: str | None) -> bool:
    return is_singular_error(error) or EMPTY_PATTERN.search(error or "") is not None


def larger_sample(data: bytes, limit: int = LARGE_MAX_ROWS) -> tuple[bytes, int]:
    frame = pd.read_parquet(io.BytesIO(data))
    if len(frame) <= limit:
        return data, len(frame)
    buffer = io.BytesIO()
    frame.sample(n=limit, random_state=LARGE_SEED).sort_index().to_parquet(buffer)
    return buffer.getvalue(), limit


def smoke_rows(outcome: Outcome) -> tuple[int, ...]:
    return () if outcome.sample_rows is None else (outcome.sample_rows,)


class LargerSample:
    def __init__(
        self, config: SmokeConfig, steps: list[Step], sample_n: int, run: Run, limit: int
    ) -> None:
        self.config = config
        self.steps = steps
        self.sample_n = sample_n
        self.run = run
        self.limit = limit
        self.rows: int | None = None
        self.parents: dict[str, Checkpoint] = {}
        self.lock = asyncio.Lock()
        self.unavailable = False

    async def _root(self) -> Checkpoint | None:
        if self.unavailable:
            return None
        if self.rows is None:
            data, rows = larger_sample(self.config.data, self.limit)
            if rows <= self.sample_n:
                self.unavailable = True
                return None
            self.rows = rows
            self.parents["__root__"] = await self.config.backend.root({harness.DATA_FILE: data})
        return self.parents["__root__"]

    async def _parent(self, step: Step) -> Checkpoint | None:
        parent = await self._root()
        if parent is None:
            return None
        for earlier in self.steps:
            if earlier.id == step.id:
                return parent
            cached = self.parents.get(earlier.id)
            if cached is None:
                live = self.config.state.defaults.get(earlier.id)
                option = live.option if live is not None else earlier.default
                checkpoint, error, _, _ = await self.run(self.config, parent, earlier, option)
                if error is not None or checkpoint is None:
                    return None
                cached = self.parents[earlier.id] = checkpoint
            parent = cached
        return parent

    async def rerun(self, step: Step, option: Option) -> tuple[Executed, int] | None:
        if self.unavailable:
            return None
        async with self.lock:
            parent = await self._parent(step)
        if parent is None or self.rows is None:
            return None
        return await self.run(self.config, parent, step, option), self.rows
