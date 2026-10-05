from __future__ import annotations

from borges.analysis import harness
from borges.analysis.path_scrub import scrub_paths
from borges.sandbox.backend import ExecResult

ERROR_TAIL_CHARS = 400
ERROR_HEAD_CHARS = 800
SANDBOX_FAILED = "the sandbox failed"


def _tail(text: str) -> str:
    return text.strip()[-ERROR_TAIL_CHARS:]


def failure_detail(run: ExecResult) -> tuple[str, bool]:
    parsed = harness.parse_error(run.stdout)
    detail = (
        (parsed[:ERROR_HEAD_CHARS] if parsed else None)
        or scrub_paths(_tail(run.stderr))
        or scrub_paths(_tail(run.stdout))
        or f"exit code {run.exit_code}"
    )
    return detail, parsed is not None


def sandbox_failed(error: str | None) -> bool:
    """A universe whose sandbox call raised failed for a reason its code cannot change.

    At d29a189 seven marp_norms universes failed within one second because the service had let an
    upload expire, and the runner rewrote the code of six options in answer to it; the same
    universes ran when they were tried again.
    """
    lines = (error or "").strip().splitlines()
    return bool(lines) and lines[0].partition(": ")[2].startswith(SANDBOX_FAILED)
