from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request

from borges.runtime.runtime import Runtime


def attach_runtime(app: FastAPI) -> Runtime | None:
    from borges.runs.orchestrator import RunOrchestrator
    from borges.runs.store import RunStore

    state: Any = app.state
    if state.runtime is not None:
        return state.runtime
    if isinstance(state.orchestrator, RunOrchestrator) and isinstance(state.store, RunStore):
        state.runtime = Runtime(
            state.settings,
            state.orchestrator,
            state.store,
            state.bus,
            upload_loader=state.uploads.get,
        )
    return state.runtime


def get_runtime(request: Request) -> Runtime | None:
    return request.app.state.runtime


def require_runtime(request: Request) -> Runtime:
    runtime = request.app.state.runtime
    if runtime is None:
        raise HTTPException(status_code=503, detail="The run queue is not available.")
    return runtime
