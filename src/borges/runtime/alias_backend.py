from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace

from borges.sandbox.backend import BranchBackend, Checkpoint, ExecResult


class AliasBackend:
    """Maps checkpoint ids recorded before a restart onto the ones rebuilt in this process."""

    def __init__(self, inner: BranchBackend) -> None:
        self.inner = inner
        self.aliases: dict[str, Checkpoint] = {}

    @property
    def name(self) -> str:
        return self.inner.name

    def _real(self, checkpoint: Checkpoint) -> Checkpoint:
        return self.aliases.get(checkpoint.id, checkpoint)

    async def root(self, files: Mapping[str, bytes]) -> Checkpoint:
        return await self.inner.root(files)

    async def run(
        self,
        parent: Checkpoint,
        command: Sequence[str],
        files: Mapping[str, bytes] | None = None,
        timeout_s: float = 120.0,
    ) -> ExecResult:
        result = await self.inner.run(self._real(parent), command, files, timeout_s)
        child = result.checkpoint
        return replace(result, checkpoint=Checkpoint(child.id, parent.id, child.backend))

    async def read_file(self, checkpoint: Checkpoint, path: str) -> bytes:
        return await self.inner.read_file(self._real(checkpoint), path)

    async def close(self) -> None:
        return None
