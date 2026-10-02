from __future__ import annotations

import io
import json
from typing import Any

import pandas as pd

from borges.analysis import harness
from borges.analysis.models import Option, Step
from borges.analysis.path_scrub import scrub_paths
from borges.analysis.smoke_types import Check, Outcome, Repair, SmokeConfig
from borges.llm.client import LLMError
from borges.sandbox.backend import Checkpoint

SMOKE_MAX_ROWS = 2000
SMOKE_FRACTION = 0.05
SMOKE_MIN_ROWS = 200
SMOKE_SEED = 7
MAX_SMOKE_REPAIRS = 2
ERROR_CHARS = 800

Executed = tuple[Checkpoint | None, str | None, dict[str, Any] | None, dict[str, Any] | None]


def sample_rows(data: bytes) -> bytes:
    frame = pd.read_parquet(io.BytesIO(data))
    target = min(SMOKE_MAX_ROWS, max(SMOKE_MIN_ROWS, int(len(frame) * SMOKE_FRACTION)))
    if len(frame) <= target:
        return data
    sample = frame.sample(n=target, random_state=SMOKE_SEED).sort_index()
    buffer = io.BytesIO()
    sample.to_parquet(buffer)
    return buffer.getvalue()


def _error_text(run_stdout: str, run_stderr: str, exit_code: int) -> str:
    parsed = harness.parse_error(run_stdout)
    text = parsed or scrub_paths(run_stderr.strip()[-ERROR_CHARS:]) or f"exit code {exit_code}"
    return text[:ERROR_CHARS]


def _trace_effects(stdout: str) -> dict[str, Any] | None:
    effects = None
    for line in stdout.splitlines():
        if not line.startswith(harness.TRACE_PREFIX):
            continue
        try:
            payload = json.loads(line[len(harness.TRACE_PREFIX) :])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("effects"), dict):
            effects = payload["effects"]
    return effects


async def execute(config: SmokeConfig, parent: Checkpoint, step: Step, option: Option) -> Executed:
    files = {
        harness.step_filename(step.id, option.id): harness.render_step(
            step, option, split_half=True
        ).encode()
    }
    try:
        run = await config.backend.run(
            parent,
            harness.step_command(step.id, option.id),
            files=files,
            timeout_s=config.timeout_s,
        )
    except Exception as exc:
        return None, scrub_paths(f"{type(exc).__name__}: {exc}")[:ERROR_CHARS], None, None
    if not run.ok:
        return None, _error_text(run.stdout, run.stderr, run.exit_code), None, None
    traces, result = harness.parse_output(run.stdout)
    if not traces:
        return None, "the step produced no trace", None, None
    return run.checkpoint, None, _trace_effects(run.stdout), result.model_dump() if result else None


async def _attempt(
    config: SmokeConfig, parent: Checkpoint, step: Step, option: Option, check: Check | None
) -> Executed:
    checkpoint, error, effects, result = await execute(config, parent, step, option)
    if error is None and check is not None:
        error = check(effects)
    if error is None and result is not None and config.result_check is not None:
        error = config.result_check(result)
    return checkpoint, error, effects, result


async def smoke_option(
    config: SmokeConfig,
    repair: Repair,
    parent: Checkpoint,
    step: Step,
    option: Option,
    check: Check | None = None,
    resume: tuple[int, list[str], str] | None = None,
    budget: int = MAX_SMOKE_REPAIRS,
) -> Outcome:
    attempts, models, error = (resume[0], list(resume[1]), resume[2]) if resume else (1, [], None)
    checkpoint = effects = result = None
    if resume is None:
        checkpoint, error, effects, result = await _attempt(config, parent, step, option, check)
    seen = [error] if error is not None else []
    used = 0
    while error is not None and used < budget:
        try:
            code, violation, model = await repair(step, option, error, attempts)
        except LLMError as exc:
            return Outcome(
                option, "failed", attempts + 1, str(exc), None, models, errors=[*seen, str(exc)]
            )
        attempts += 1
        used += 1
        models.append(model)
        option = option.model_copy(update={"code": code})
        if violation is not None:
            error = violation
            seen.append(error)
            continue
        checkpoint, error, effects, result = await _attempt(config, parent, step, option, check)
        if error is not None:
            seen.append(error)
    if error is not None:
        return Outcome(option, "failed", attempts, error, None, models, effects, result, seen)
    status = "passed" if attempts == 1 else "repaired"
    return Outcome(option, status, attempts, None, checkpoint, models, effects, result)
