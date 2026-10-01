from __future__ import annotations

from collections.abc import Awaitable, Callable

from borges.analysis.models import AnalysisPlan, Option, Step
from borges.llm.client import LLMClient

OnCoded = Callable[[str, str, bool, int, str | None], Awaitable[None]]


async def code_option(
    llm: LLMClient, plan: AnalysisPlan, step: Step, option: Option, error: str | None = None
) -> str:
    raise NotImplementedError


async def code_plan(
    llm: LLMClient, plan: AnalysisPlan, on_coded: OnCoded | None = None, concurrency: int = 6
) -> AnalysisPlan:
    raise NotImplementedError


async def repair_option(
    llm: LLMClient, plan: AnalysisPlan, step: Step, option: Option, error: str
) -> Option:
    raise NotImplementedError
