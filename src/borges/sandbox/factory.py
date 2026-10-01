from __future__ import annotations

from typing import Literal

from borges.config import Settings
from borges.sandbox.backend import BranchBackend


def make_backend(
    settings: Settings, kind: Literal["local", "contree"] | None = None
) -> BranchBackend:
    raise NotImplementedError
