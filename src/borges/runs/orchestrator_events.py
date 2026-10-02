from __future__ import annotations

import logging
import time
from typing import Literal, cast

from borges.config import Settings
from borges.fleet.models import RunAgents
from borges.runs.bus import EventBus
from borges.runs.emitter import RunEmitter
from borges.runs.events import (
    RunCancelledData,
    RunFailedData,
    RunFinishedData,
    RunStartedData,
)
from borges.runs.inputs import ResolvedRun
from borges.runs.models import RunRequest
from borges.runs.orchestrator_meta import announced_models, outcome_meta
from borges.runs.pipeline import Pipeline
from borges.runs.store import RunStore

log = logging.getLogger("borges.run")


async def announce(
    emitter: RunEmitter,
    settings: Settings,
    request: RunRequest,
    resolved: ResolvedRun,
    modes: tuple[str, str],
    trace_id: str | None = None,
    agents: RunAgents | None = None,
) -> None:
    llm, backend = modes
    started = RunStartedData(
        case_id=resolved.case_id,
        title=resolved.title,
        question=resolved.question,
        decision_rule=resolved.decision_rule.model_dump(mode="json"),
        mode="live",
        llm=cast(Literal["nebius", "scripted", "local"], llm),
        backend=backend,
        models=announced_models(settings, llm),
        max_universes=resolved.max_universes,
        trace_id=trace_id,
        agents=agents,
    )
    await emitter.emit("run.started", started.model_dump(mode="json"))


async def finish(
    store: RunStore,
    bus: EventBus,
    emitter: RunEmitter,
    started_at: float,
    error: str | None,
    pipeline: Pipeline | None,
    cancelled: str | None = None,
) -> None:
    status = "cancelled" if cancelled else "failed" if error else "completed"
    finished = RunFinishedData(
        status=cast(Literal["completed", "failed", "cancelled"], status),
        elapsed_s=time.monotonic() - started_at,
    )
    meta: dict[str, object] = {"status": status}
    if pipeline is not None:
        meta.update(outcome_meta(pipeline))
    try:
        store.update_meta(emitter.run_id, **meta)
        if cancelled:
            await emitter.emit("run.cancelled", RunCancelledData(reason=cancelled).model_dump())
        elif error:
            await emitter.emit("run.failed", RunFailedData(error=error).model_dump())
        await emitter.emit("run.finished", finished.model_dump(mode="json"))
    finally:
        bus.close(emitter.run_id)
    log.info("run %s", status, extra={"run_id": emitter.run_id, "status": status})
