from __future__ import annotations

from borges.analysis.models import AnalysisPlan, Proposal
from borges.garden.models import Universe
from borges.llm.client import LLMClient


async def propose_options(
    llm: LLMClient, plan: AnalysisPlan, baseline: Universe, max_proposals: int = 4
) -> list[Proposal]:
    raise NotImplementedError
