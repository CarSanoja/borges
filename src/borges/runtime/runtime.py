from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import secrets
import socket
import time
from collections.abc import Callable
from typing import Any

from borges.config import Settings
from borges.identity.principal import Principal
from borges.identity.run_quota import RunQuota
from borges.runs.bus import EventBus
from borges.runs.models import RunRequest
from borges.runs.orchestrator import RunOrchestrator
from borges.runs.store import RunStore
from borges.runtime.admission import make_admit
from borges.runtime.checkpoints import SqliteCheckpointStore
from borges.runtime.context import CancelToken
from borges.runtime.db import RuntimeDb, open_runtime_db
from borges.runtime.dead_letter import DeadLetters
from borges.runtime.finalize import append_terminal
from borges.runtime.idempotency import derived_key, explicit_key
from borges.runtime.jobs import ACTIVE_STATES, Job, SubmitResult
from borges.runtime.maintenance import drain_queue, owner_is_dead, reclaim
from borges.runtime.queue import IdempotencyKey, JobQueue
from borges.runtime.schedules import ScheduleStore
from borges.runtime.submission import may_cancel, submit_run
from borges.runtime.worker import run_job

log = logging.getLogger("borges.runtime")
UploadLoader = Callable[[str], tuple[bytes, str]]


class Runtime:
    """Durable job queue, lease-holding workers, resume, retries, cancel and schedules."""

    def __init__(
        self,
        settings: Settings,
        orchestrator: RunOrchestrator,
        store: RunStore,
        bus: EventBus,
        upload_loader: UploadLoader | None = None,
        db: RuntimeDb | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.settings = settings
        self.orchestrator = orchestrator
        self.store = store
        self.bus = bus
        self.upload_loader = upload_loader
        self.db = db or open_runtime_db(settings)
        self.queue = JobQueue(self.db, clock)
        self.dead = DeadLetters(self.db, clock)
        self.checkpoints = SqliteCheckpointStore(self.db)
        self.schedules = ScheduleStore(self.db, clock)
        self.owner = f"{socket.gethostname()}:{os.getpid()}:{secrets.token_hex(4)}"
        self.tokens: dict[str, CancelToken] = {}
        self.jobs: dict[str, asyncio.Task[None]] = {}
        self._admit = make_admit(settings)
        self._loop_task: asyncio.Task[None] | None = None
        self._wakeup: asyncio.Event | None = None
        self._changed: asyncio.Event | None = None
        self._scheduled_at = 0.0
        self._started = False

    def wake(self) -> None:
        if self._wakeup is not None:
            self._wakeup.set()
        if self._changed is not None:
            self._changed.set()

    def load_upload(self, upload_id: str) -> tuple[bytes, str]:
        if self.upload_loader is None:
            raise KeyError(upload_id)
        return self.upload_loader(upload_id)

    def is_active(self, run_id: str) -> bool:
        job = self.queue.get(run_id)
        return job is not None and job.state in ACTIVE_STATES

    def known_run_ids(self) -> set[str]:
        return self.queue.active_run_ids()

    def stats(self) -> dict[str, Any]:
        return self.queue.stats()

    def idempotency(
        self, principal: Principal, client: str, request: RunRequest, header: str | None
    ) -> IdempotencyKey:
        if header:
            return explicit_key(principal.id, header)
        return derived_key(RunQuota.owner_key(principal, client), request, self.settings)

    def lookup(self, key: IdempotencyKey) -> str | None:
        return self.queue.lookup(key)

    async def submit(
        self,
        request: RunRequest,
        principal: Principal,
        client: str,
        key: IdempotencyKey | None = None,
        data: bytes | None = None,
        dataset_name: str | None = None,
        source: str = "api",
        schedule_id: str | None = None,
    ) -> SubmitResult:
        result = await submit_run(
            self, request, principal, client, key, data, dataset_name, source, schedule_id
        )
        if result.created:
            await self.start()
            await self.dispatch()
        return result

    def authorized(self, job: Job, principal: Principal, client: str) -> bool:
        return may_cancel(job, principal, client)

    async def cancel(self, run_id: str) -> str:
        outcome = self.queue.request_cancel(run_id)
        if outcome == "cancelled":
            append_terminal(
                self.store, self.bus, run_id, "cancelled", "cancelled before it started"
            )
            self.checkpoints.clear(run_id)
        elif outcome == "requested":
            token = self.tokens.get(run_id)
            if token is not None:
                token.set("cancelled by request")
        return outcome

    def requeue(self, run_id: str) -> Job | None:
        job = self.dead.requeue(run_id)
        if job is not None:
            self.store.update_meta(run_id, status="queued")
            self.wake()
        return job

    async def dispatch(self) -> int:
        launched = 0
        while True:
            job = self.queue.claim(self.owner, self.settings.borges_job_lease_s, self._admit)
            if job is None:
                return launched
            self.store.update_meta(job.run_id, status="running")
            worker = asyncio.create_task(run_job(self, job))
            self.jobs[job.run_id] = worker
            worker.add_done_callback(lambda done, r=job.run_id: self._forget(r, done))
            launched += 1

    def _forget(self, run_id: str, worker: asyncio.Task[None]) -> None:
        if self.jobs.get(run_id) is worker:
            del self.jobs[run_id]

    def recover(self) -> int:
        return self.queue.expire_leases_where(owner_is_dead)

    def maintain(self) -> None:
        reclaim(self)

    async def tick(self) -> None:
        self.maintain()
        if self.settings.borges_scheduler:
            now = time.time()
            if now - self._scheduled_at >= self.settings.borges_scheduler_poll_s:
                self._scheduled_at = now
                from borges.runtime.scheduler import run_due

                await run_due(self)
        await self.dispatch()

    async def _loop(self) -> None:
        assert self._wakeup is not None
        while True:
            try:
                await self.tick()
            except Exception:
                log.exception("runtime tick failed")
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._wakeup.wait(), self.settings.borges_runtime_poll_s)
            self._wakeup.clear()

    async def drain(self, wait_s: float) -> bool:
        assert self._changed is not None
        return await drain_queue(self.queue, self._changed, wait_s)

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._wakeup = asyncio.Event()
        self._changed = asyncio.Event()
        self.recover()
        self._loop_task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        loop_task, self._loop_task = self._loop_task, None
        self._started = False
        if loop_task is not None:
            loop_task.cancel()
            await asyncio.gather(loop_task, return_exceptions=True)
        pending = list(self.jobs.values())
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
