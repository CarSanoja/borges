from __future__ import annotations

import re

from borges.analysis.models import AnalysisPlan
from borges.analysis.narrative_counts import drop_wrong_counts
from borges.analysis.narrative_flip import (
    drop_wrong_sentences,
    flip_sentence,
    has_sentence,
    insert_sentence,
    problems,
)
from borges.analysis.narrative_ids import drop_option_ids
from borges.analysis.narrative_no_flip import no_flip_problems, rewrite_claimed_flips
from borges.analysis.narrative_original import original_problems, with_original
from borges.analysis.narrative_repeats import drop_prompt_echoes, drop_repeated_sentences
from borges.analysis.narrative_robustness import (
    drop_inverted_sentences,
    drop_method_sentences,
    inverted_shares,
    robustness_sentence,
)
from borges.analysis.narrative_scale import drop_unit_readings, unit_readings
from borges.analysis.narrator_garden import estimate_tokens, garden_digest
from borges.analysis.prompts.narrator import RULES, SCALE_LABEL, build_messages
from borges.analysis.schemas import NarratorOutput
from borges.garden.models import Garden, Report
from borges.garden.outcome_scale import mentions_log_scale, scale_note
from borges.llm.client import LLMClient, LLMError, Role
from borges.runs.judged_ledger import JudgedLedger

NUMBER = re.compile(r"\d")
MISSING_FLIP = "the flip sentence is missing"


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
    """Errors in what the narrator wrote. A required sentence it left out is not one: the
    original, flip and robustness sentences are added afterwards."""
    found = [
        *original_problems(plan, report, narrative),
        *(p for p in problems(plan, report, narrative) if not p.startswith(MISSING_FLIP)),
        *inverted_shares(report, narrative),
        *no_flip_problems(report, narrative),
    ]
    if scale is not None and (
        unit_readings(report, narrative, scale) or not mentions_log_scale(narrative)
    ):
        found.append(f"it reads the estimate as additional units of the outcome, but {scale}")
    return found


def _clean(plan: AnalysisPlan, report: Report, text: str) -> str:
    echoes = drop_option_ids(plan, drop_prompt_echoes(text, RULES, (SCALE_LABEL,)))
    return drop_wrong_counts(report, drop_method_sentences(report, drop_repeated_sentences(echoes)))


def _complete(
    plan: AnalysisPlan, report: Report, narrative: str, sentence: str | None, scale: str | None
) -> str:
    units = unit_readings(report, narrative, scale)
    narrative = rewrite_claimed_flips(report, drop_unit_readings(report, narrative, scale))
    kept = with_original(plan, report, narrative)
    if sentence is not None and not has_sentence(kept, sentence):
        kept = insert_sentence(kept, sentence)
    robust = robustness_sentence(report)
    if robust is not None and not has_sentence(kept, robust):
        head = robust.split(". ", 1)[0] + "."
        flat = " ".join(kept.split())
        kept = flat.replace(head, robust) if head != robust and head in flat else f"{kept} {robust}"
    if scale is not None and (units or not mentions_log_scale(kept)):
        kept = insert_sentence(kept, scale)
    return kept


async def narrate(
    llm: LLMClient,
    plan: AnalysisPlan,
    report: Report,
    garden: Garden | None = None,
    judged: JudgedLedger | None = None,
) -> str:
    sentence = flip_sentence(plan, report)
    scale = scale_note(garden) if garden is not None else None
    out = await _ask(llm, plan, report, sentence, "narrator", None, garden, judged, scale)
    narrative = _clean(plan, report, out.narrative)
    issues = _issues(plan, report, narrative, scale)
    if issues:
        try:
            retry = await _ask(
                llm, plan, report, sentence, "narrator:retry", issues, garden, judged, scale
            )
        except LLMError:
            retry = None
        second = _clean(plan, report, retry.narrative) if retry is not None else ""
        if retry is not None and not _issues(plan, report, second, scale) and NUMBER.search(second):
            narrative = second
        else:
            narrative = drop_inverted_sentences(
                report, drop_wrong_sentences(plan, report, narrative)
            )
    return _complete(plan, report, narrative, sentence, scale)
