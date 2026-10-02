from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from borges.api import (
    routes_agents,
    routes_cases,
    routes_health,
    routes_identity,
    routes_memory,
    routes_policy,
    routes_run_create,
    routes_runs,
    routes_runtime,
    routes_trace,
    routes_uploads,
)
from borges.api.body_limit import BodyLimitMiddleware
from borges.api.runtime_wiring import attach_runtime
from borges.api.spa import mount_frontend
from borges.api.startup import reconcile, warn_unkeyed
from borges.api.uploads import UploadStore
from borges.config import Settings, get_settings
from borges.gateway.errors import PolicyError
from borges.identity.authentication import Authenticator
from borges.identity.chain import ChainBroken
from borges.identity.middleware import IdentityMiddleware
from borges.identity.rate_limit import RateLimiter
from borges.identity.run_quota import RunQuota
from borges.telemetry.run_telemetry import anchor_global_audit

CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def _build_missing(app: FastAPI) -> None:
    from borges.cases.registry import CaseRegistry
    from borges.runs.bus import EventBus
    from borges.runs.orchestrator import RunOrchestrator
    from borges.runs.store import RunStore

    state: Any = app.state
    settings: Settings = state.settings
    if state.registry is None:
        state.registry = CaseRegistry(settings.borges_cases_dir)
    if state.store is None:
        state.store = RunStore(settings.borges_runs_dir)
    if state.bus is None:
        state.bus = EventBus(state.store)
    if state.orchestrator is None:
        state.orchestrator = RunOrchestrator(settings, state.store, state.bus, state.registry)


def create_app(
    settings: Settings | None = None,
    orchestrator: Any = None,
    registry: Any = None,
    store: Any = None,
    bus: Any = None,
) -> FastAPI:
    resolved = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        _build_missing(app)
        warn_unkeyed(resolved)
        runtime = attach_runtime(app)
        await asyncio.to_thread(
            reconcile, resolved, app.state.store, app.state.orchestrator, runtime
        )
        if runtime is not None:
            await runtime.start()
        yield
        if runtime is not None:
            await runtime.stop()
        shutdown = getattr(app.state.orchestrator, "shutdown", None)
        if shutdown is not None:
            await shutdown()
        await asyncio.to_thread(anchor_global_audit, resolved)

    app = FastAPI(title="Borges", lifespan=lifespan)
    app.state.settings = resolved
    app.state.orchestrator = orchestrator
    app.state.registry = registry
    app.state.store = store
    app.state.bus = bus
    app.state.runtime = None
    app.state.uploads = UploadStore(
        resolved.borges_home / "uploads", resolved.borges_upload_quota_mb
    )
    attach_runtime(app)

    app.add_middleware(BodyLimitMiddleware)
    app.state.authenticator = Authenticator(resolved)
    app.state.limiter = RateLimiter(resolved)
    app.state.run_quota = RunQuota(resolved)
    app.add_middleware(
        IdentityMiddleware,
        settings=resolved,
        routes_of=lambda: app.routes,
        authenticator=app.state.authenticator,
        limiter=app.state.limiter,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(PolicyError)
    async def _policy_error(_: Request, error: PolicyError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(error)})

    @app.exception_handler(ChainBroken)
    async def _chain_broken(_: Request, error: ChainBroken) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(error)})

    for module in (
        routes_health,
        routes_memory,
        routes_identity,
        routes_cases,
        routes_policy,
        routes_agents,
        routes_runtime,
        routes_run_create,
        routes_runs,
        routes_trace,
        routes_uploads,
    ):
        app.include_router(module.router, prefix="/api")
    mount_frontend(app, resolved.borges_frontend_dist)
    return app
