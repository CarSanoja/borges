from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from borges.runs.models import RunRequest, RunSnapshot
from borges.runtime import audit
from borges.runtime.context import CancelToken, RunContext, RunRetry
from borges.runtime.finalize import append_terminal
from borges.runtime.jobs import CANCELLED, FAILED, SUCCEEDED, Job

if TYPE_CHECKING:
    from borges.runtime.runtime import Runtime

log = logging.getLogger("borges.runtime")
MAX_BACKOFF_S = 300.0


def backoff_s(base: float, attempts: int) -> float:
    return min(MAX_BACKOFF_S, base * (2 ** max(0, attempts - 1)))


async def _heartbeat(
    runtime: Runtime, job: Job, token: CancelToken, task: asyncio.Task[RunSnapshot]
) -> None:
    lease_s = runtime.settings.borges_job_lease_s
    while True:
        await asyncio.sleep(max(0.02, lease_s / 3))
        beat = runtime.queue.heartbeat(job.run_id, runtime.owner, lease_s)
        if not beat.held:
            log.warning("lease lost", extra={"run_id": job.run_id})
            task.cancel()
            return
        if beat.cancel:
            token.set("cancelled by request")


def _context(runtime: Runtime, job: Job, token: CancelToken) -> RunContext:
    has_progress = any(e.type == "run.started" for e in runtime.store.events(job.run_id))
    return RunContext(
        run_id=job.run_id,
        checkpoints=runtime.checkpoints,
        cancel=token,
        attempt=job.attempts,
        max_attempts=job.max_attempts,
        resume_reason=(job.resume_reason or "restart") if has_progress else None,
    )


async def _settle(runtime: Runtime, job: Job, context: RunContext, snapshot: RunSnapshot) -> None:
    run_id = job.run_id
    if snapshot.status == "completed":
        runtime.queue.finish(run_id, runtime.owner, SUCCEEDED)
        runtime.checkpoints.clear(run_id)
    elif snapshot.status == "cancelled":
        runtime.queue.finish(run_id, runtime.owner, CANCELLED, snapshot.error)
        audit.record(runtime.settings, "runtime.run.cancelled", data={"run_id": run_id})
    elif context.transient_failure:
        error = snapshot.error or "transient failure"
        last = runtime.checkpoints.last(run_id)
        if runtime.dead.bury(run_id, runtime.owner, error, last):
            audit.record(
                runtime.settings,
                "runtime.dead_letter",
                decision="deny",
                reason=error[:300],
                data={"run_id": run_id, "attempts": job.attempts},
            )
    else:
        runtime.queue.finish(run_id, runtime.owner, FAILED, snapshot.error)


async def _retry(runtime: Runtime, job: Job, retry: RunRetry) -> None:
    delay = backoff_s(runtime.settings.borges_job_backoff_s, job.attempts)
    if runtime.queue.retry(job.run_id, runtime.owner, retry.error, delay):
        runtime.store.update_meta(job.run_id, status="queued", last_error=retry.error)
        runtime.wake()
        audit.record(
            runtime.settings,
            "runtime.run.retry",
            reason=retry.error[:300],
            data={"run_id": job.run_id, "attempt": job.attempts, "delay_s": delay},
        )


def _load(runtime: Runtime, job: Job) -> tuple[bytes | None, str | None]:
    if job.upload_id is None:
        return None, None
    return runtime.load_upload(job.upload_id)


async def run_job(runtime: Runtime, job: Job) -> None:
    run_id = job.run_id
    request = RunRequest.model_validate_json(job.request)
    token = CancelToken()
    if job.cancel_requested:
        token.set("cancelled by request")
    runtime.tokens[run_id] = token
    try:
        data, name = _load(runtime, job)
    except KeyError:
        error = "the uploaded dataset is no longer available"
        append_terminal(runtime.store, runtime.bus, run_id, "failed", error)
        runtime.queue.finish(run_id, runtime.owner, FAILED, error)
        runtime.tokens.pop(run_id, None)
        return
    context = _context(runtime, job, token)
    task = runtime.orchestrator.launch(run_id, request, data, name, context)
    beat = asyncio.create_task(_heartbeat(runtime, job, token, task))
    try:
        snapshot = await task
    except RunRetry as retry:
        await _retry(runtime, job, retry)
    except asyncio.CancelledError:
        runtime.queue.release(run_id, runtime.owner)
        current = asyncio.current_task()
        if current is not None and current.cancelling():
            raise
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        log.exception("job failed", extra={"run_id": run_id})
        append_terminal(runtime.store, runtime.bus, run_id, "failed", error)
        runtime.queue.finish(run_id, runtime.owner, FAILED, error)
    else:
        await _settle(runtime, job, context, snapshot)
    finally:
        beat.cancel()
        runtime.tokens.pop(run_id, None)
        runtime.wake()
