from __future__ import annotations

import asyncio
import io
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import pandas as pd

from borges.analysis import harness
from borges.analysis.models import AnalysisPlan, CodingSummary, Option, Step
from borges.analysis.path_scrub import scrub_paths
from borges.llm.client import LLMError
from borges.sandbox.backend import BranchBackend, Checkpoint

SMOKE_MAX_ROWS = 2000
SMOKE_FRACTION = 0.05
SMOKE_MIN_ROWS = 200
SMOKE_SEED = 7
MAX_SMOKE_REPAIRS = 2
ERROR_CHARS = 800

OnSmoke = Callable[[str, str, str, int, str | None, list[str]], Awaitable[None]]
Repair = Callable[[Step, Option, str, int], Awaitable[tuple[str, str | None, str]]]


@dataclass
class SmokeConfig:
    backend: BranchBackend
    data: bytes
    on_smoke: OnSmoke | None = None
    timeout_s: float = 60.0


@dataclass
class _Outcome:
    option: Option
    status: str
    attempts: int
    error: str | None
    checkpoint: Checkpoint | None
    models: list[str]


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


async def _execute(
    config: SmokeConfig, parent: Checkpoint, step: Step, option: Option
) -> tuple[Checkpoint | None, str | None]:
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
        return None, scrub_paths(f"{type(exc).__name__}: {exc}")[:ERROR_CHARS]
    if not run.ok:
        return None, _error_text(run.stdout, run.stderr, run.exit_code)
    traces, _ = harness.parse_output(run.stdout)
    if not traces:
        return None, "the step produced no trace"
    return run.checkpoint, None


async def _smoke_option(
    config: SmokeConfig, repair: Repair, parent: Checkpoint, step: Step, option: Option
) -> _Outcome:
    attempts = 1
    models: list[str] = []
    checkpoint, error = await _execute(config, parent, step, option)
    while error is not None and attempts <= MAX_SMOKE_REPAIRS:
        try:
            code, violation, model = await repair(step, option, error, attempts)
        except LLMError as exc:
            return _Outcome(option, "failed", attempts + 1, str(exc), None, models)
        attempts += 1
        models.append(model)
        option = option.model_copy(update={"code": code})
        if violation is not None:
            error = violation
            continue
        checkpoint, error = await _execute(config, parent, step, option)
    if error is not None:
        return _Outcome(option, "failed", attempts, error, None, models)
    status = "passed" if attempts == 1 else "repaired"
    return _Outcome(option, status, attempts, None, checkpoint, models)


async def _smoke_step(
    config: SmokeConfig,
    repair: Repair,
    parent: Checkpoint,
    step: Step,
    semaphore: asyncio.Semaphore,
) -> list[_Outcome]:
    async def work(option: Option) -> _Outcome:
        async with semaphore:
            outcome = await _smoke_option(config, repair, parent, step, option)
        if config.on_smoke is not None:
            await config.on_smoke(
                step.id, option.id, outcome.status, outcome.attempts, outcome.error, outcome.models
            )
        return outcome

    return list(await asyncio.gather(*(work(o) for o in step.options if o.code is not None)))


def _record(summary: CodingSummary | None, outcomes: list[_Outcome]) -> None:
    if summary is None:
        return
    summary.smoke_tested += len(outcomes)
    summary.repaired_after_smoke += sum(1 for o in outcomes if o.status == "repaired")
    summary.failed += sum(1 for o in outcomes if o.status == "failed")


def _apply(step: Step, outcomes: list[_Outcome]) -> tuple[Checkpoint, Option | None, str]:
    default_id = step.default.id
    survivors = {o.option.id: o for o in outcomes if o.status != "failed"}
    step.options = [survivors[o.id].option for o in step.options if o.id in survivors]
    if default_id not in survivors:
        failed = next((o for o in outcomes if o.option.id == default_id), None)
        if not step.options:
            reason = failed.error if failed else "not coded"
            raise LLMError(f"default option {step.id}.{default_id} failed its smoke run: {reason}")
        step.options[0].is_default = True
        reason = failed.error if failed and failed.error else "not coded"
        return survivors[step.default.id].checkpoint, step.options[0], f"{default_id}: {reason}"
    return survivors[step.default.id].checkpoint, None, ""


async def smoke_plan(
    config: SmokeConfig,
    plan: AnalysisPlan,
    repair: Repair,
    summary: CodingSummary | None = None,
    concurrency: int = 6,
) -> AnalysisPlan:
    smoked = plan.model_copy(deep=True)
    parent = await config.backend.root({harness.DATA_FILE: sample_rows(config.data)})
    semaphore = asyncio.Semaphore(concurrency)
    for step in smoked.steps:
        outcomes = await _smoke_step(config, repair, parent, step, semaphore)
        _record(summary, outcomes)
        parent, promoted, cause = _apply(step, outcomes)
        if promoted is not None and config.on_smoke is not None:
            chosen = next(o for o in outcomes if o.option.id == promoted.id)
            note = f"promoted to default because {cause} failed its smoke run"
            await config.on_smoke(
                step.id, promoted.id, chosen.status, chosen.attempts, note, chosen.models
            )
    return smoked
