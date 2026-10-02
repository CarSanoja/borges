from __future__ import annotations

from pathlib import Path

import pandas as pd

from borges.analysis import harness
from borges.analysis.models import Option, Step
from borges.sandbox.backend import Checkpoint, ExecResult
from borges.sandbox.local_backend import LocalBackend


def make_step(code: str, kind: str = "filter") -> tuple[Step, Option]:
    option = Option(id="o1", label="l", rationale="r", spec="s", is_default=True, code=code)
    step = Step(id="s1", title="t", kind=kind, description="d", options=[option])
    return step, option


def frame_bytes() -> bytes:
    path = Path(__file__).parent / "_policy_frame.parquet"
    pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [2.0, 4.1, 5.9, 8.2]}).to_parquet(path)
    try:
        return path.read_bytes()
    finally:
        path.unlink()


async def run_step(
    backend: LocalBackend,
    code: str,
    kind: str = "filter",
    root_files: dict[str, bytes] | None = None,
    policy_home: str | None = None,
    policy_audit_path: str | None = None,
) -> tuple[ExecResult, str | None]:
    step, option = make_step(code, kind)
    root = await backend.root({harness.DATA_FILE: frame_bytes(), **(root_files or {})})
    rendered = harness.render_step(step, option, policy_home, policy_audit_path)
    files = {harness.step_filename(step.id, option.id): rendered.encode()}
    result = await backend.run(root, harness.step_command(step.id, option.id), files=files)
    return result, harness.parse_error(result.stdout)


def checkpoint_files(backend: LocalBackend, checkpoint: Checkpoint) -> set[str]:
    base = backend._fs(checkpoint.id)
    return {str(p.relative_to(base)) for p in base.rglob("*") if p.is_file()}
