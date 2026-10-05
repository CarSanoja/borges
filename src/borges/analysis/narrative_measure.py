"""The measure the original analysis reports, named as fitted.

A red_cards summary at a491fe1 opened with "estimated an odds ratio of 1.14": the decision rule
names an odds ratio, but the original analysis fitted a Poisson model and reported a rate ratio.
In the clause about the original analysis, the first other ratio's name becomes the fitted one.
"""

from __future__ import annotations

import re

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
RATIO = re.compile(r"\b(?:an?\s+)?(?:odds|(?:incidence\s+)?rate|risk)\s+ratio\b", re.IGNORECASE)
ORIGINAL = re.compile(r"\boriginal analysis\b", re.IGNORECASE)
CLAUSE_END = re.compile(r"[,;]|\b(?:while|whereas|but)\b")


def _a(measure: str) -> str:
    return f"an {measure}" if measure[0] in "aeiou" else f"a {measure}"


def name_original_measure(narrative: str, fitted: str | None) -> str:
    if fitted is None:
        return narrative

    def rename(match: re.Match[str]) -> str:
        text = match.group(0)
        if fitted in text.lower():
            return text
        return _a(fitted) if re.match(r"an?\s", text, re.IGNORECASE) else fitted

    out = []
    for sentence in _SENTENCE_END.split(narrative.strip()):
        found = ORIGINAL.search(sentence)
        if found is None:
            out.append(sentence)
            continue
        end = CLAUSE_END.search(sentence, found.end())
        stop = end.start() if end else len(sentence)
        clause = RATIO.sub(rename, sentence[found.start() : stop], count=1)
        out.append(sentence[: found.start()] + clause + sentence[stop:])
    return " ".join(out)
