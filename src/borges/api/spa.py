from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from borges.cases.registry import CaseRegistry
from borges.runs.store import RunStore

CLIENT_ROUTE = re.compile(r"^(?:|fleet|memory|platform|replay/[^/]+|run/[^/]+(?:/trace)?)/?$")
ID_ROUTE = re.compile(r"^(run|replay)/([^/]+?)(?:/trace)?/?$")


def is_client_route(path: str) -> bool:
    return CLIENT_ROUTE.fullmatch(path) is not None


def _known_id(request: Request, path: str) -> bool:
    match = ID_ROUTE.fullmatch(path)
    if match is None:
        return True
    kind, ident = match.groups()
    state = request.app.state
    settings = state.settings
    if kind == "run":
        store = state.store or RunStore(settings.borges_runs_dir)
        return store.exists(ident)
    registry = state.registry or CaseRegistry(settings.borges_cases_dir)
    try:
        registry.get(ident)
    except KeyError:
        return False
    return True


def mount_frontend(app: FastAPI, dist: Path) -> None:
    index = dist / "index.html"
    if not index.exists():
        return
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")
    root = dist.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str, request: Request) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found.")
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        status = 200 if is_client_route(path) and _known_id(request, path) else 404
        return FileResponse(index, status_code=status)
