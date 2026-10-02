from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from borges.telemetry.hashing import sha256_text


class CodeEvidence:
    def __init__(self) -> None:
        self._codes: dict[str, str] = {}

    def record(self, code: str) -> None:
        body = code.rstrip("\n")
        if body:
            self._codes[sha256_text(body)] = body

    def covers(self, text: str) -> bool:
        from borges.analysis.step_shape import is_rendered_step

        return any(is_rendered_step(text, body) for body in self._codes.values())

    def __len__(self) -> int:
        return len(self._codes)


_CURRENT: ContextVar[CodeEvidence | None] = ContextVar("borges_code_evidence", default=None)


def record_guarded(code: str) -> None:
    evidence = _CURRENT.get()
    if evidence is not None:
        evidence.record(code)


@contextmanager
def collecting(evidence: CodeEvidence) -> Iterator[CodeEvidence]:
    token = _CURRENT.set(evidence)
    try:
        yield evidence
    finally:
        _CURRENT.reset(token)
