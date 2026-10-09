"""A decision rule written out is not an order to report a label.

The A/B planner wrote its default as "if ci_low > 0, output decision = 'SHIP'; else decision =
'DON'T SHIP'" and steering.report_label stopped the run (r_20261009T020850_267ffb). A rule that
tests a quantity and names both branches leaves the label to the data; an order names one label
unconditionally. A match counts as a branch when a comparison of a quantity opens its sentence and
an else, otherwise or "si no" follows within 160 characters with a different label.
"""

from __future__ import annotations

import re

from borges.armor.patterns_goal import OUTCOME

BRANCHED = frozenset({"steering.report_label"})
SENTENCE_END = re.compile(r"[.;\n](?=\s|$)")
CONDITION = re.compile(
    r"\b(?:if|when|si|cuando)\b[^,:]{0,60}?(?:<=|>=|<|>|==|\bexceeds?\b|\bbelow\b|\babove\b|"
    r"\bsupera\b|\bmenor\b|\bmayor\b)",
    re.IGNORECASE,
)
OTHER_BRANCH = re.compile(
    r"\b(?:else|otherwise|si\s+no|de\s+lo\s+contrario|en\s+otro\s+caso)\b", re.IGNORECASE
)
LOOKAROUND = 160
LABEL = re.compile(rf"\b{OUTCOME}\b", re.IGNORECASE)


def _clause_start(text: str, start: int) -> int:
    window = text[max(0, start - LOOKAROUND) : start]
    ends = [m.end() for m in SENTENCE_END.finditer(window)]
    return start - len(window) + (ends[-1] if ends else 0)


def _labels(text: str) -> set[str]:
    return {re.sub(r"\W+", " ", m.group(0).lower()) for m in LABEL.finditer(text)}


def is_decision_branch(text: str, start: int, end: int) -> bool:
    opening = text[_clause_start(text, start) : start]
    other = OTHER_BRANCH.search(text, end, end + LOOKAROUND)
    if not CONDITION.search(opening) or other is None:
        return False
    branch = text[other.end() : other.end() + LOOKAROUND]
    return bool(_labels(branch) - _labels(text[start:end]))
