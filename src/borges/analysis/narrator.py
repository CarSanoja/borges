from __future__ import annotations

import re

from borges.analysis.models import AnalysisPlan
from borges.analysis.narrative_flip import (
    drop_wrong_sentences,
    flip_sentence,
    has_sentence,
    insert_sentence,
    problems,
)
from borges.analysis.narrative_original import original_problems, with_original
from borges.analysis.narrative_repeats import drop_prompt_echoes, drop_repeated_sentences
from borges.analysis.narrative_robustness import (
    drop_inverted_sentences,
    kept_caveats,
    robustness_problems,
    robustness_sentence,
)
from borges.analysis.narrator_garden import estimate_tokens, garden_digest
from borges.analysis.prompts.narrator import RULES, build_messages
from borges.analysis.schemas import NarratorOutput
from borges.garden.models import Garden, Report
from borges.garden.outcome_scale import mentions_log_scale, scale_note
from borges.llm.client import LLMClient, LLMError, Role
from borges.runs.judged_ledger import JudgedLedger

NUMBER = re.compile(r"\d")


def _messages(
    plan: AnalysisPlan,
    report: Report,
    sentence: str | None,
    issues: list[str] | None,
    garden: Garden | None,
    judged: JudgedLedger | None,
    scale: str | None = None,
) -> list[dict[str, str]]:
    if garden is None:
        return build_messages(plan, report, sentence, issues, scale=scale)
    fixed = sum(
        estimate_tokens(m["content"])
        for m in build_messages(plan, report, sentence, issues, {}, scale)
    )
    digest, _ = garden_digest(plan, garden, judged, list(report.caveats), fixed_tokens=fixed)
    return build_messages(plan, report, sentence, issues, digest, scale)


async def _ask(
    llm: LLMClient,
    plan: AnalysisPlan,
    report: Report,
    sentence: str | None,
    key: str,
    issues: list[str] | None = None,
    garden: Garden | None = None,
    judged: JudgedLedger | None = None,
    scale: str | None = None,
) -> NarratorOutput:
    messages = _messages(plan, report, sentence, issues, garden, judged, scale)
    report.narrator_input_tokens = sum(estimate_tokens(m["content"]) for m in messages)
    response = await llm.complete(
        Role.NARRATOR,
        messages,
        key=key,
        schema=NarratorOutput,
        max_tokens=1200,
    )
    return NarratorOutput.model_validate(response.parsed)


def _issues(plan: AnalysisPlan, report: Report, narrative: str, scale: str | None) -> list[str]:
    found = [
        *original_problems(plan, report, narrative),
        *problems(plan, report, narrative),
        *robustness_problems(report, narrative),
    ]
    if scale is not None and not mentions_log_scale(narrative):
        found.append(f"it reads the estimate as additional units of the outcome, but {scale}")
    return found


async def narrate(
    llm: LLMClient,
    plan: AnalysisPlan,
    report: Report,
    garden: Garden | None = None,
    judged: JudgedLedger | None = None,
) -> tuple[str, list[str]]:
    sentence = flip_sentence(plan, report)
    scale = scale_note(garden) if garden is not None else None
    out = await _ask(llm, plan, report, sentence, "narrator", None, garden, judged, scale)
    narrative = drop_repeated_sentences(drop_prompt_echoes(out.narrative, RULES))
    issues = _issues(plan, report, narrative, scale)
    if not issues:
        return narrative, kept_caveats(report, out.caveats)
    try:
        retry = await _ask(
            llm, plan, report, sentence, "narrator:retry", issues, garden, judged, scale
        )
    except LLMError:
        retry = None
    if retry is not None:
        second = drop_repeated_sentences(drop_prompt_echoes(retry.narrative, RULES))
        if not _issues(plan, report, second, scale) and NUMBER.search(second):
            return second, kept_caveats(report, retry.caveats)
    kept = drop_inverted_sentences(report, drop_wrong_sentences(plan, report, narrative))
    kept = with_original(plan, report, kept)
    if sentence is not None and not has_sentence(kept, sentence):
        kept = insert_sentence(kept, sentence)
    robust = robustness_sentence(report)
    if robust is not None and not has_sentence(kept, robust):
        kept = f"{kept} {robust}"
    if scale is not None and not mentions_log_scale(kept):
        kept = insert_sentence(kept, scale)
    return kept, kept_caveats(report, out.caveats)
