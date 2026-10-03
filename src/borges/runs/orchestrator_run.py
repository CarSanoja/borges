from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from borges.armor.report import ArmorReport
from borges.fleet.models import RunAgents
from borges.gateway.core import Gateway
from borges.runs.emitter import RunEmitter
from borges.runs.inputs import ResolvedRun
from borges.runs.models import RunRequest, RunSnapshot
from borges.runs.orchestrator_build import build_backend, build_gateway_and_llm, build_memory
from borges.runs.orchestrator_events import announce, finish
from borges.runs.pipeline import Pipeline
from borges.runtime.context import RunCancelled, RunContext, RunRetry
from borges.runtime.resume import ResumePlan, plan_resume
from borges.sandbox.backend import BranchBackend
from borges.telemetry.run_telemetry import RunTelemetry

if TYPE_CHECKING:
    from borges.runs.orchestrator import RunOrchestrator

log = logging.getLogger("borges.run")


def _emitter(
    orchestrator: RunOrchestrator, run_id: str, context: RunContext | None
) -> tuple[RunEmitter, ResumePlan | None]:
    if context is None or not context.resumed:
        return RunEmitter(run_id, orchestrator.store, orchestrator.bus), None
    plan = plan_resume(orchestrator.store, orchestrator.bus, context)
    emitter = RunEmitter(run_id, orchestrator.store, orchestrator.bus, plan.replay, plan.last_seq)
    return emitter, plan


async def run_pipeline(
    orchestrator: RunOrchestrator,
    run_id: str,
    request: RunRequest,
    resolved: ResolvedRun,
    telemetry: RunTelemetry | None,
    agents: RunAgents | None = None,
    context: RunContext | None = None,
) -> RunSnapshot:
    orchestrator.bus.open(run_id)
    started_at = time.monotonic()
    emitter, resume = _emitter(orchestrator, run_id, context)
    pipeline: Pipeline | None = None
    backend: BranchBackend | None = None
    gateway: Gateway | None = None
    error: str | None = None
    try:
        if resume is not None and resume.announced:
            await emitter.emit("run.resumed", resume.event())
        else:
            trace_id = telemetry.trace_id if telemetry else None
            modes = orchestrator.modes(request)
            await announce(
                emitter, orchestrator.settings, request, resolved, modes, trace_id, agents
            )
        log.info("run started", extra={"run_id": run_id, "case_id": resolved.case_id})
        armor_report = ArmorReport()
        gateway, llm = build_gateway_and_llm(orchestrator, run_id, request, resolved, armor_report)
        backend = build_backend(orchestrator, request, gateway)
        memory = build_memory(
            orchestrator,
            run_id,
            request,
            resolved,
            agents,
            armor_report,
            context is not None and context.resumed,
        )
        pipeline = Pipeline(
            orchestrator.settings, llm, backend, emitter, resolved, armor_report, memory
        )
        pipeline.agents = agents
        pipeline.context = context
        pipeline.restored = resume.restored if resume and resume.restored else None
        with gateway.bind():
            await pipeline.run()
    except RunCancelled as cancelled:
        reason = str(cancelled) or "cancelled"
        await finish(
            orchestrator.store, orchestrator.bus, emitter, started_at, None, pipeline, reason
        )
        return orchestrator.snapshot(run_id)
    except asyncio.CancelledError:
        if context is None:
            await finish(
                orchestrator.store, orchestrator.bus, emitter, started_at, "run cancelled", pipeline
            )
        else:
            orchestrator.bus.close(run_id)
        raise
    except Exception as exc:
        if context is not None and context.failed(exc):
            raise RunRetry(f"{type(exc).__name__}: {exc}") from exc
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if gateway is not None:
            gateway.budgets.release_outstanding()
        if backend is not None:
            await backend.close()
    await finish(orchestrator.store, orchestrator.bus, emitter, started_at, error, pipeline)
    return orchestrator.snapshot(run_id)
