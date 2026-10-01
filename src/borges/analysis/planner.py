from __future__ import annotations

from borges.analysis.models import AnalysisPlan, DatasetProfile, DecisionRule
from borges.llm.client import LLMClient


async def plan_analysis(
    llm: LLMClient, profile: DatasetProfile, question: str, rule: DecisionRule
) -> AnalysisPlan:
    raise NotImplementedError
