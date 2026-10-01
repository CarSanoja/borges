from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

WORKDIR = "/borges"


class SandboxError(RuntimeError):
    pass


@dataclass(frozen=True)
class Checkpoint:
    id: str
    parent_id: str | None
    backend: str


@dataclass(frozen=True)
class ExecResult:
    checkpoint: Checkpoint
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


@runtime_checkable
class BranchBackend(Protocol):
    """Branchable execution: every run forks a parent checkpoint into a new one.

    Paths in `files` and in `read_file` are relative to the sandbox working directory.
    Commands run with that directory as cwd and `python` resolving to an interpreter that
    has pandas, numpy, scipy, statsmodels and pyarrow installed.
    """

    name: str

    async def root(self, files: Mapping[str, bytes]) -> Checkpoint: ...

    async def run(
        self,
        parent: Checkpoint,
        command: Sequence[str],
        files: Mapping[str, bytes] | None = None,
        timeout_s: float = 120.0,
    ) -> ExecResult: ...

    async def read_file(self, checkpoint: Checkpoint, path: str) -> bytes: ...

    async def close(self) -> None: ...
