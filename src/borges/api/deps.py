from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

from borges.api.uploads import UploadStore
from borges.config import Settings

if TYPE_CHECKING:
    from borges.cases.registry import CaseRegistry
    from borges.runs.bus import EventBus
    from borges.runs.orchestrator import RunOrchestrator
    from borges.runs.store import RunStore


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_orchestrator(request: Request) -> RunOrchestrator:
    return request.app.state.orchestrator


def get_registry(request: Request) -> CaseRegistry:
    return request.app.state.registry


def get_store(request: Request) -> RunStore:
    return request.app.state.store


def get_bus(request: Request) -> EventBus:
    return request.app.state.bus


def get_uploads(request: Request) -> UploadStore:
    return request.app.state.uploads
