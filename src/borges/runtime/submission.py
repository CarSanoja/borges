from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from borges.identity.principal import Principal
from borges.identity.run_access import run_is_public
from borges.identity.run_quota import RunQuota
from borges.identity.scopes import ADMIN
from borges.runs.inputs import resolve_run
from borges.runs.models import RunRequest
from borges.runs.orchestrator import new_run_id
from borges.runtime.jobs import Job, NewJob, SubmitResult
from borges.runtime.queue import IdempotencyKey

if TYPE_CHECKING:
    from borges.runtime.runtime import Runtime


async def submit_run(
    runtime: Runtime,
    request: RunRequest,
    principal: Principal,
    client: str,
    key: IdempotencyKey | None,
    data: bytes | None,
    dataset_name: str | None,
    source: str,
    schedule_id: str | None,
) -> SubmitResult:
    if key is not None:
        existing = runtime.queue.lookup(key)
        if existing is not None:
            return SubmitResult(existing, False)
    orchestrator = runtime.orchestrator
    resolved = await asyncio.to_thread(
        resolve_run, request, orchestrator.registry, runtime.settings, data, dataset_name
    )
    run_id = new_run_id()
    owner_key = RunQuota.owner_key(principal, client)
    orchestrator.register(
        run_id,
        request,
        resolved,
        status="queued",
        extra={
            "principal": principal.id,
            "owner_key": owner_key,
            "source": source,
            "public": run_is_public(resolved.case_id, request.upload_id is not None, principal),
        },
    )
    job = NewJob(
        run_id=run_id,
        principal=principal.id,
        owner_key=owner_key,
        anonymous=principal.anonymous,
        live=orchestrator.is_live(request),
        request=request.model_dump_json(exclude_none=True),
        max_attempts=runtime.settings.borges_job_max_attempts,
        source=source,
        schedule_id=schedule_id,
        upload_id=request.upload_id,
        dataset_name=dataset_name,
    )
    result = runtime.queue.submit(job, key)
    if not result.created:
        runtime.store.discard(run_id)
        runtime.bus.close(run_id)
    return result


def may_cancel(job: Job, principal: Principal, client: str) -> bool:
    if principal.has(ADMIN):
        return True
    if principal.anonymous:
        return job.anonymous and job.owner_key == RunQuota.owner_key(principal, client)
    return job.principal == principal.id
