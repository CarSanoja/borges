from __future__ import annotations

from borges.analysis.models import AnalysisPlan, Judgement, Option, Step
from borges.llm.client import LLMClient


async def judge_option(llm: LLMClient, plan: AnalysisPlan, step: Step, option: Option) -> Judgement:
    raise NotImplementedError
