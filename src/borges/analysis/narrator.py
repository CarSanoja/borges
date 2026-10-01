from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.analysis.prompts.narrator import build_messages
from borges.analysis.schemas import NarratorOutput
from borges.garden.models import Report
from borges.llm.client import LLMClient, Role


async def narrate(llm: LLMClient, plan: AnalysisPlan, report: Report) -> tuple[str, list[str]]:
    response = await llm.complete(
        Role.NARRATOR,
        build_messages(plan, report),
        key="narrator",
        schema=NarratorOutput,
        max_tokens=1200,
    )
    out = NarratorOutput.model_validate(response.parsed)
    return out.narrative.strip(), list(out.caveats)
