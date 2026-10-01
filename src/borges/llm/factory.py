from __future__ import annotations

from pathlib import Path
from typing import Literal

from borges.config import Settings
from borges.llm.client import LLMClient


def make_llm(
    settings: Settings,
    mode: Literal["nebius", "scripted"] | None = None,
    fixtures_dir: Path | None = None,
    record_dir: Path | None = None,
    run_cap_usd: float | None = None,
) -> LLMClient:
    raise NotImplementedError
