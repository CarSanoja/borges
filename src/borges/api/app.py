from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from borges.api import routes_cases, routes_health, routes_runs, routes_uploads
from borges.api.startup import reconcile
from borges.api.uploads import UploadStore
from borges.config import Settings, get_settings

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


def _mount_frontend(app: FastAPI, dist: Path) -> None:
    index = dist / "index.html"
    if not index.exists():
        return
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found.")
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(dist.resolve()):
            return FileResponse(candidate)
        return FileResponse(index)


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
        await asyncio.to_thread(reconcile, resolved, app.state.store, app.state.orchestrator)
        yield
        shutdown = getattr(app.state.orchestrator, "shutdown", None)
        if shutdown is not None:
            await shutdown()

    app = FastAPI(title="Borges", lifespan=lifespan)
    app.state.settings = resolved
    app.state.orchestrator = orchestrator
    app.state.registry = registry
    app.state.store = store
    app.state.bus = bus
    app.state.uploads = UploadStore(
        resolved.borges_home / "uploads", resolved.borges_upload_quota_mb
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for module in (routes_health, routes_cases, routes_runs, routes_uploads):
        app.include_router(module.router, prefix="/api")
    _mount_frontend(app, resolved.borges_frontend_dist)
    return app
