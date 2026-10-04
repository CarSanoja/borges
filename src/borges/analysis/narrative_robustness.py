from __future__ import annotations

import re

from borges.garden.models import Report

SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
PERCENT = re.compile(r"(\d{1,3})\s?%")
REVERSES = re.compile(
    r"\b(?:flipped|flips? (?:the|its) (?:verdict|conclusion)|revers\w*|overturn\w*)\b", re.I
)
AGREES = re.compile(r"\b(?:agree\w*|support\w*|consistent|robust\w*|same verdict)\b", re.I)
METHOD = re.compile(r"\bbeam\b|\bagreement rate\b|\bexplored region\b", re.I)


def robustness_sentence(report: Report) -> str | None:
    if report.n_universes == 0:
        return None
    agree = round(report.robustness * 100)
    if report.robustness_basis == "design_weighted":
        return (
            f"Robustness: {agree}% of the analysis grid agrees with the original verdict and "
            f"{100 - agree}% reverses it."
        )
    return (
        f"Robustness: {agree}% of the distinct results agree with the original verdict and "
        f"{100 - agree}% reverse it."
    )


def _agree_shares(report: Report) -> set[int]:
    shares = [report.robustness, report.robustness_beam, report.robustness_design]
    return {round(share * 100) for share in shares if share is not None}


def inverted_shares(report: Report, narrative: str) -> list[str]:
    agree = {share for share in _agree_shares(report) if share != 50}
    found: list[str] = []
    for sentence in SENTENCE_END.split(narrative.strip()):
        numbers = {int(n) for n in PERCENT.findall(sentence)}
        if REVERSES.search(sentence) and not AGREES.search(sentence):
            found += [
                f"it says {n}% reverse the verdict, but {n}% is the share that agrees with it"
                for n in sorted(numbers & agree)
            ]
        if AGREES.search(sentence) and not REVERSES.search(sentence):
            found += [
                f"it says {n}% agree with the verdict, but {n}% is the share that reverses it"
                for n in sorted(numbers & {100 - share for share in agree})
            ]
    return found


def robustness_problems(report: Report, narrative: str) -> list[str]:
    sentence = robustness_sentence(report)
    found = inverted_shares(report, narrative)
    if sentence is not None and " ".join(sentence.split()) not in " ".join(narrative.split()):
        found.append(f"the robustness sentence is missing: {sentence}")
    return found


def drop_inverted_sentences(report: Report, narrative: str) -> str:
    kept = [s for s in SENTENCE_END.split(narrative.strip()) if not inverted_shares(report, s)]
    return " ".join(kept)


def kept_caveats(report: Report, caveats: list[str]) -> list[str]:
    """The deterministic robustness sentence and caveats state the basis of the share; a narrator
    caveat that describes the search method again, or inverts a share, is dropped."""
    return [c for c in caveats if not METHOD.search(c) and not inverted_shares(report, c)]
