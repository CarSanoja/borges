from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Report
from borges.llm.client import LLMClient


async def narrate(llm: LLMClient, plan: AnalysisPlan, report: Report) -> tuple[str, list[str]]:
    raise NotImplementedError
