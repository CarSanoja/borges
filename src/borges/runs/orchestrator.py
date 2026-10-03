from __future__ import annotations

import asyncio
import logging
import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from borges.cases.registry import CaseRegistry
from borges.config import Settings
from borges.fleet.models import RunAgents
from borges.llm.factory import make_llm
from borges.runs.bus import EventBus
from borges.runs.detail import build_universe_detail
from borges.runs.inputs import ResolvedRun, resolve_run
from borges.runs.models import RunRequest, RunSnapshot, UniverseDetail
from borges.runs.orchestrator_meta import agents_provenance, new_run_meta
from borges.runs.orchestrator_run import run_pipeline
from borges.runs.orchestrator_trace import (
    TelemetryFactory,
    close_telemetry,
    mark_outcome,
    open_telemetry,
    run_scope,
)
from borges.runs.ownership import owner_fields
from borges.runs.store import RunStore
from borges.runtime.context import RunContext
from borges.sandbox.factory import make_backend
from borges.telemetry.run_telemetry import RunTelemetry

log = logging.getLogger("borges.run")


def new_run_id() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    return f"r_{stamp}_{secrets.token_hex(3)}"


class RunOrchestrator:
    def __init__(
        self,
        settings: Settings,
        store: RunStore,
        bus: EventBus,
        registry: CaseRegistry,
        llm_factory: Callable = make_llm,
        backend_factory: Callable = make_backend,
        record_dir: Path | None = None,
        telemetry_factory: TelemetryFactory = RunTelemetry.open,
    ) -> None:
        self.settings = settings
        self.store = store
        self.bus = bus
        self.registry = registry
        self.llm_factory = llm_factory
        self.backend_factory = backend_factory
        self.record_dir = record_dir
        self.telemetry_factory = telemetry_factory
        self.tasks: dict[str, asyncio.Task[RunSnapshot]] = {}
        self._live: set[str] = set()

    def active_count(self) -> int:
        return len(self.tasks)

    def live_count(self) -> int:
        return len(self._live & self.tasks.keys())

    def is_live(self, request: RunRequest) -> bool:
        return self.modes(request)[0] == "nebius"

    def modes(self, request: RunRequest) -> tuple[str, str]:
        return (
            request.llm or self.settings.borges_llm,
            request.backend or self.settings.borges_backend,
        )

    def register(
        self,
        run_id: str,
        request: RunRequest,
        resolved: ResolvedRun,
        status: str = "running",
        extra: dict[str, object] | None = None,
    ) -> None:
        meta = new_run_meta(resolved, *self.modes(request), status, extra)
        self.store.create(run_id, meta)
        self.bus.open(run_id)

    async def start(
        self,
        request: RunRequest,
        data: bytes | None = None,
        dataset_name: str | None = None,
    ) -> str:
        resolved = await asyncio.to_thread(
            resolve_run, request, self.registry, self.settings, data, dataset_name
        )
        run_id = new_run_id()
        self.register(run_id, request, resolved)
        self.launch(run_id, request, data, dataset_name)
        return run_id

    def launch(
        self,
        run_id: str,
        request: RunRequest,
        data: bytes | None = None,
        dataset_name: str | None = None,
        context: RunContext | None = None,
    ) -> asyncio.Task[RunSnapshot]:
        task = asyncio.create_task(self.execute(run_id, request, data, dataset_name, context))
        self.tasks[run_id] = task
        self._live.update([run_id] if self.modes(request)[0] == "nebius" else [])
        task.add_done_callback(lambda _: self._forget(run_id))
        return task

    def _forget(self, run_id: str) -> None:
        self.tasks.pop(run_id, None)
        self._live.discard(run_id)

    async def wait(self, run_id: str) -> RunSnapshot:
        task = self.tasks.get(run_id)
        if task is not None:
            await asyncio.shield(task)
        return self.snapshot(run_id)

    async def shutdown(self) -> None:
        pending = list(self.tasks.values())
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    def snapshot(self, run_id: str) -> RunSnapshot:
        return self.store.snapshot(run_id)

    def universe_detail(self, run_id: str, universe_id: str) -> UniverseDetail:
        return build_universe_detail(self.snapshot(run_id), universe_id)

    async def execute(
        self,
        run_id: str,
        request: RunRequest,
        data: bytes | None = None,
        dataset_name: str | None = None,
        context: RunContext | None = None,
    ) -> RunSnapshot:
        resolved = await asyncio.to_thread(
            resolve_run, request, self.registry, self.settings, data, dataset_name
        )
        if not self.store.exists(run_id):
            self.register(run_id, request, resolved)
        if context is not None:
            self.store.update_meta(
                run_id, status="running", attempt=context.attempt, **owner_fields()
            )
        telemetry = open_telemetry(self.telemetry_factory, self.settings, self.store, run_id)
        llm_mode, backend_mode = self.modes(request)
        agents = agents_provenance(self.settings, llm_mode)
        if agents is not None:
            self.store.update_meta(run_id, agents=agents.model_dump(mode="json"))
        attributes = {
            "borges.case_id": resolved.case_id or "",
            "borges.llm": llm_mode,
            "borges.backend": backend_mode,
        }
        try:
            with run_scope(telemetry, self.store, run_id, attributes) as span:
                snapshot = await self._execute(
                    run_id, request, resolved, telemetry, agents, context
                )
                mark_outcome(span, snapshot.status)
                return snapshot
        finally:
            close_telemetry(telemetry, self.store, run_id)

    async def _execute(
        self,
        run_id: str,
        request: RunRequest,
        resolved: ResolvedRun,
        telemetry: RunTelemetry | None,
        agents: RunAgents | None = None,
        context: RunContext | None = None,
    ) -> RunSnapshot:
        return await run_pipeline(self, run_id, request, resolved, telemetry, agents, context)
