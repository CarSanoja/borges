from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.analysis.narrative_flip import (
    drop_wrong_sentences,
    flip_sentence,
    insert_sentence,
    problems,
)
from borges.analysis.narrative_repeats import drop_repeated_sentences
from borges.analysis.narrator_garden import estimate_tokens, garden_digest
from borges.analysis.prompts.narrator import build_messages
from borges.analysis.schemas import NarratorOutput
from borges.garden.models import Garden, Report
from borges.llm.client import LLMClient, LLMError, Role
from borges.runs.judged_ledger import JudgedLedger


def _messages(
    plan: AnalysisPlan,
    report: Report,
    sentence: str | None,
    issues: list[str] | None,
    garden: Garden | None,
    judged: JudgedLedger | None,
) -> list[dict[str, str]]:
    if garden is None:
        return build_messages(plan, report, sentence, issues)
    fixed = sum(
        estimate_tokens(m["content"]) for m in build_messages(plan, report, sentence, issues, {})
    )
    digest, _ = garden_digest(plan, garden, judged, list(report.caveats), fixed_tokens=fixed)
    return build_messages(plan, report, sentence, issues, digest)


async def _ask(
    llm: LLMClient,
    plan: AnalysisPlan,
    report: Report,
    sentence: str | None,
    key: str,
    issues: list[str] | None = None,
    garden: Garden | None = None,
    judged: JudgedLedger | None = None,
) -> NarratorOutput:
    messages = _messages(plan, report, sentence, issues, garden, judged)
    report.narrator_input_tokens = sum(estimate_tokens(m["content"]) for m in messages)
    response = await llm.complete(
        Role.NARRATOR,
        messages,
        key=key,
        schema=NarratorOutput,
        max_tokens=1200,
    )
    return NarratorOutput.model_validate(response.parsed)


async def narrate(
    llm: LLMClient,
    plan: AnalysisPlan,
    report: Report,
    garden: Garden | None = None,
    judged: JudgedLedger | None = None,
) -> tuple[str, list[str]]:
    sentence = flip_sentence(plan, report)
    out = await _ask(llm, plan, report, sentence, "narrator", None, garden, judged)
    narrative = drop_repeated_sentences(out.narrative.strip())
    issues = problems(plan, report, narrative)
    if not issues or sentence is None:
        return narrative, list(out.caveats)
    try:
        retry = await _ask(llm, plan, report, sentence, "narrator:retry", issues, garden, judged)
        narrative, out = drop_repeated_sentences(retry.narrative.strip()), retry
    except LLMError:
        pass
    if problems(plan, report, narrative):
        narrative = insert_sentence(drop_wrong_sentences(plan, report, narrative), sentence)
    return narrative, list(out.caveats)
