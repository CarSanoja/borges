from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from borges.runtime.checkpoints import CheckpointStore
from borges.runtime.transient import is_transient


class RunCancelled(BaseException):
    """Raised at a checkpoint when the run was asked to stop."""


class RunRetry(Exception):
    """A transient failure that the runtime will retry from the last checkpoint."""

    def __init__(self, error: str) -> None:
        super().__init__(error)
        self.error = error


class CancelToken:
    def __init__(self) -> None:
        self._reason: str | None = None

    def set(self, reason: str = "cancelled") -> None:
        if self._reason is None:
            self._reason = reason

    def is_set(self) -> bool:
        return self._reason is not None

    @property
    def reason(self) -> str | None:
        return self._reason


@dataclass
class RunContext:
    run_id: str
    checkpoints: CheckpointStore
    cancel: CancelToken = field(default_factory=CancelToken)
    attempt: int = 1
    max_attempts: int = 1
    resume_reason: str | None = None
    transient_failure: bool = False

    @property
    def resumed(self) -> bool:
        return self.resume_reason is not None

    def check(self) -> None:
        if self.cancel.is_set():
            raise RunCancelled(self.cancel.reason)

    def save(self, key: str, seq: int, payload: dict[str, Any]) -> None:
        self.checkpoints.save(self.run_id, key, seq, payload)

    def failed(self, error: Exception) -> bool:
        transient = is_transient(error)
        self.transient_failure = transient
        return transient and self.attempt < self.max_attempts
