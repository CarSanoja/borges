from __future__ import annotations

import asyncio
import logging
import secrets
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

from borges.armor.llm_armor import LLMArmor
from borges.armor.report import ArmorReport
from borges.cases.registry import CaseRegistry
from borges.config import Settings
from borges.fleet.models import RunAgents
from borges.gateway.core import build_gateway
from borges.gateway.dataset_columns import columns_of
from borges.llm.factory import make_llm
from borges.runs.bus import EventBus
from borges.runs.detail import build_universe_detail
from borges.runs.emitter import RunEmitter
from borges.runs.events import RunFailedData, RunFinishedData, RunStartedData
from borges.runs.inputs import ResolvedRun, resolve_run
from borges.runs.models import RunRequest, RunSnapshot, UniverseDetail
from borges.runs.orchestrator_identity import mint_identity
from borges.runs.orchestrator_meta import agents_provenance, announced_models, outcome_meta
from borges.runs.orchestrator_trace import (
    TelemetryFactory,
    close_telemetry,
    mark_outcome,
    open_telemetry,
    run_scope,
)
from borges.runs.ownership import owner_fields
from borges.runs.pipeline import Pipeline
from borges.runs.state import fold
from borges.runs.store import RunStore
from borges.sandbox.backend import BranchBackend
from borges.sandbox.factory import make_backend
from borges.telemetry.instrumented_backend import instrument_backend
from borges.telemetry.instrumented_llm import instrument_llm
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

    def _modes(self, request: RunRequest) -> tuple[str, str]:
        return (
            request.llm or self.settings.borges_llm,
            request.backend or self.settings.borges_backend,
        )

    def _register(self, run_id: str, request: RunRequest, resolved: ResolvedRun) -> None:
        llm, backend = self._modes(request)
        self.store.create(
            run_id,
            {
                "case_id": resolved.case_id,
                "title": resolved.title,
                "status": "running",
                "created_at": time.time(),
                "llm": llm,
                "backend": backend,
                "cost_usd": 0.0,
                "n_universes": 0,
                "verdict": None,
                "flipped_verdict": None,
                **owner_fields(),
            },
        )
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
        self._register(run_id, request, resolved)
        task = asyncio.create_task(self.execute(run_id, request, data, dataset_name))
        self.tasks[run_id] = task
        self._live.update([run_id] if self._modes(request)[0] == "nebius" else [])
        task.add_done_callback(lambda _: self._forget(run_id))
        return run_id

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
        return fold(self.store.events(run_id), run_id)

    def universe_detail(self, run_id: str, universe_id: str) -> UniverseDetail:
        return build_universe_detail(self.snapshot(run_id), universe_id)

    async def _announce(
        self,
        emitter: RunEmitter,
        request: RunRequest,
        resolved: ResolvedRun,
        trace_id: str | None = None,
        agents: RunAgents | None = None,
    ) -> None:
        llm, backend = self._modes(request)
        started = RunStartedData(
            case_id=resolved.case_id,
            title=resolved.title,
            question=resolved.question,
            decision_rule=resolved.decision_rule.model_dump(mode="json"),
            mode="live",
            llm=cast(Literal["nebius", "scripted", "local"], llm),
            backend=backend,
            models=announced_models(self.settings, llm),
            max_universes=resolved.max_universes,
            trace_id=trace_id,
            agents=agents,
        )
        await emitter.emit("run.started", started.model_dump(mode="json"))

    async def _finish(
        self, emitter: RunEmitter, started_at: float, error: str | None, pipeline: Pipeline | None
    ) -> None:
        status = "failed" if error else "completed"
        finished = RunFinishedData(status=status, elapsed_s=time.monotonic() - started_at)
        meta: dict[str, object] = {"status": status}
        if pipeline is not None:
            meta.update(outcome_meta(pipeline))
        try:
            self.store.update_meta(emitter.run_id, **meta)
            if error:
                await emitter.emit("run.failed", RunFailedData(error=error).model_dump())
            await emitter.emit("run.finished", finished.model_dump(mode="json"))
        finally:
            self.bus.close(emitter.run_id)
        log.info("run %s", status, extra={"run_id": emitter.run_id, "status": status})

    async def execute(
        self,
        run_id: str,
        request: RunRequest,
        data: bytes | None = None,
        dataset_name: str | None = None,
    ) -> RunSnapshot:
        resolved = await asyncio.to_thread(
            resolve_run, request, self.registry, self.settings, data, dataset_name
        )
        if not self.store.exists(run_id):
            self._register(run_id, request, resolved)
        telemetry = open_telemetry(self.telemetry_factory, self.settings, self.store, run_id)
        llm_mode, backend_mode = self._modes(request)
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
                snapshot = await self._execute(run_id, request, resolved, telemetry, agents)
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
    ) -> RunSnapshot:
        self.bus.open(run_id)
        started_at = time.monotonic()
        emitter = RunEmitter(run_id, self.store, self.bus)
        pipeline: Pipeline | None = None
        backend: BranchBackend | None = None
        error: str | None = None
        try:
            await self._announce(
                emitter, request, resolved, telemetry.trace_id if telemetry else None, agents
            )
            log.info("run started", extra={"run_id": run_id, "case_id": resolved.case_id})
            llm_options: dict[str, Path | None] = {"fixtures_dir": resolved.fixtures_dir}
            if self.record_dir is not None:
                llm_options["record_dir"] = self.record_dir
            identity = mint_identity(self.settings, run_id)
            armor_report = ArmorReport()
            gateway = build_gateway(
                self.settings,
                run_id,
                identity,
                self._modes(request)[0],
                armor=LLMArmor(armor_report),
                dataset_columns=columns_of(resolved.data),
            )
            llm = instrument_llm(
                self.llm_factory(self.settings, request.llm, **llm_options), identity, gateway
            )
            backend = instrument_backend(
                self.backend_factory(self.settings, request.backend), gateway
            )
            pipeline = Pipeline(self.settings, llm, backend, emitter, resolved, armor_report)
            pipeline.agents = agents
            with gateway.bind():
                await pipeline.run()
        except asyncio.CancelledError:
            await self._finish(emitter, started_at, "run cancelled", pipeline)
            raise
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        finally:
            if backend is not None:
                await backend.close()
        await self._finish(emitter, started_at, error, pipeline)
        return self.snapshot(run_id)
