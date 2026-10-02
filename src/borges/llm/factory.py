from __future__ import annotations

from pathlib import Path
from typing import Literal

from borges.config import Settings
from borges.llm.cache import DiskCache
from borges.llm.client import LLMClient, LLMError
from borges.llm.local_models import local_role_models, ollama_thinking_body
from borges.llm.nebius_provider import NebiusLLM
from borges.llm.scripted_provider import ScriptedLLM
from borges.llm.spend import RunBudget, SpendLedger


def make_llm(
    settings: Settings,
    mode: Literal["nebius", "scripted", "local"] | None = None,
    fixtures_dir: Path | None = None,
    record_dir: Path | None = None,
    run_cap_usd: float | None = None,
) -> LLMClient:
    chosen = mode or settings.borges_llm
    if chosen == "scripted":
        if fixtures_dir is None:
            raise LLMError("scripted mode requires a fixtures directory")
        return ScriptedLLM(fixtures_dir)
    if chosen == "local":
        return NebiusLLM(
            api_key="ollama",
            base_url=settings.borges_local_base_url,
            role_models=local_role_models(settings.borges_local_model),
            thinking_body=ollama_thinking_body,
            retry_truncated_without_thinking=True,
            cache=DiskCache(settings.borges_home / "llm-cache"),
            record_dir=record_dir,
        )
    if not settings.nebius_api_key:
        raise LLMError("NEBIUS_API_KEY is not set")
    return NebiusLLM(
        api_key=settings.nebius_api_key,
        base_url=settings.nebius_base_url,
        cache=DiskCache(settings.borges_home / "llm-cache"),
        ledger=SpendLedger(settings.borges_home / "spend.json", settings.borges_spend_cap_usd),
        run_budget=RunBudget(run_cap_usd or settings.borges_run_cap_usd),
        record_dir=record_dir,
    )
