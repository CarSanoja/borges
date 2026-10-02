from __future__ import annotations

import uuid
from typing import Literal

from borges.config import Settings
from borges.sandbox.backend import BranchBackend, SandboxError


def make_backend(
    settings: Settings, kind: Literal["local", "contree"] | None = None
) -> BranchBackend:
    chosen = kind or settings.borges_backend
    if chosen == "local":
        from borges.sandbox.limits import ResourceLimits
        from borges.sandbox.local_backend import LocalBackend

        home = settings.borges_home / "sandboxes" / f"sb_{uuid.uuid4().hex[:12]}"
        limits = ResourceLimits(
            memory_mb=settings.borges_sandbox_memory_mb,
            cpu_s=settings.borges_sandbox_cpu_s,
            fsize_mb=settings.borges_sandbox_fsize_mb,
        )
        return LocalBackend(home, ephemeral=True, limits=limits)
    if chosen == "contree":
        from borges.sandbox.contree_backend import ContreeBackend

        key = settings.contree_api_key or settings.nebius_api_key
        if not key:
            raise SandboxError(
                "the contree backend needs an API key: set CONTREE_API_KEY (or NEBIUS_API_KEY)"
            )
        project = settings.sandbox_project_id
        if not project:
            raise SandboxError(
                "the contree backend needs the Nebius project id: set NEBIUS_PROJECT_ID"
            )
        return ContreeBackend(api_key=key, base_url=settings.contree_base_url, project_id=project)
    raise SandboxError(f"unknown sandbox backend: {chosen!r}")
