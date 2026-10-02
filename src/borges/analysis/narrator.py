from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.analysis.narrative_flip import (
    drop_wrong_sentences,
    flip_sentence,
    insert_sentence,
    problems,
)
from borges.analysis.prompts.narrator import build_messages
from borges.analysis.schemas import NarratorOutput
from borges.garden.models import Report
from borges.llm.client import LLMClient, LLMError, Role


async def _ask(
    llm: LLMClient,
    plan: AnalysisPlan,
    report: Report,
    sentence: str | None,
    key: str,
    issues: list[str] | None = None,
) -> NarratorOutput:
    response = await llm.complete(
        Role.NARRATOR,
        build_messages(plan, report, sentence, issues),
        key=key,
        schema=NarratorOutput,
        max_tokens=1200,
    )
    return NarratorOutput.model_validate(response.parsed)


async def narrate(llm: LLMClient, plan: AnalysisPlan, report: Report) -> tuple[str, list[str]]:
    sentence = flip_sentence(plan, report)
    out = await _ask(llm, plan, report, sentence, "narrator")
    narrative = out.narrative.strip()
    issues = problems(plan, report, narrative)
    if not issues or sentence is None:
        return narrative, list(out.caveats)
    try:
        retry = await _ask(llm, plan, report, sentence, "narrator:retry", issues)
        narrative, out = retry.narrative.strip(), retry
    except LLMError:
        pass
    if problems(plan, report, narrative):
        narrative = insert_sentence(drop_wrong_sentences(plan, report, narrative), sentence)
    return narrative, list(out.caveats)
