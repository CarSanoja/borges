from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from borges.analysis.models import AnalysisResult, StepTrace
from borges.sandbox.backend import Checkpoint

Prefix = tuple[tuple[str, str, str], ...]


@dataclass(frozen=True)
class PrefixNode:
    checkpoint: Checkpoint | None
    traces: list[StepTrace] = field(default_factory=list)
    result: AnalysisResult | None = None
    error: str | None = None
    cacheable: bool = True

    @property
    def ok(self) -> bool:
        return self.error is None and self.checkpoint is not None


class PrefixCache:
    """Computes each prefix at most once, even when universes request it concurrently."""

    def __init__(self) -> None:
        self._nodes: dict[Prefix, PrefixNode] = {}
        self._locks: dict[Prefix, asyncio.Lock] = {}

    def seed(self, prefix: Prefix, node: PrefixNode) -> None:
        self._nodes[prefix] = node

    async def get_or_compute(
        self, prefix: Prefix, compute: Callable[[], Awaitable[PrefixNode]]
    ) -> PrefixNode:
        lock = self._locks.setdefault(prefix, asyncio.Lock())
        async with lock:
            node = self._nodes.get(prefix)
            if node is None:
                node = await compute()
                if node.cacheable:
                    self._nodes[prefix] = node
            return node
