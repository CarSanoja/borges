from __future__ import annotations

from typing import Literal

from borges.config import Settings
from borges.sandbox.backend import BranchBackend, SandboxError


def make_backend(
    settings: Settings, kind: Literal["local", "contree"] | None = None
) -> BranchBackend:
    chosen = kind or settings.borges_backend
    if chosen == "local":
        from borges.sandbox.local_backend import LocalBackend

        return LocalBackend(settings.borges_home)
    if chosen == "contree":
        from borges.sandbox.contree_backend import ContreeBackend

        key = settings.contree_api_key or settings.nebius_api_key
        if not key:
            raise SandboxError(
                "the contree backend needs an API key: set CONTREE_API_KEY (or NEBIUS_API_KEY)"
            )
        if not settings.contree_base_url:
            raise SandboxError("the contree backend needs CONTREE_BASE_URL to be set")
        return ContreeBackend(api_key=key, base_url=settings.contree_base_url)
    raise SandboxError(f"unknown sandbox backend: {chosen!r}")
