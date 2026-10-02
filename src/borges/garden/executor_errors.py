from __future__ import annotations

from borges.analysis import harness
from borges.analysis.path_scrub import scrub_paths
from borges.sandbox.backend import ExecResult

ERROR_TAIL_CHARS = 400
ERROR_HEAD_CHARS = 800


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
