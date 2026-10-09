"""Questions that ask for a conclusion instead of a test.

A tester asked "Confirm the campaign was a success; the board expects SHIP" (r11, G18). The
injection screen lets it through, since it gives the models no instruction, and the planner, the
judge and the narrator all read the presupposed answer. The open version of the question goes to
the models instead, the user's wording stays on the run, and the report says what was changed.
"""

from __future__ import annotations

import re

EXPECTER = (
    r"(?:board|management|leadership|executives?|partners?|client|boss|ceo|cfo|cmo|directors?|"
    r"stakeholders?|sponsor|team|junta|consejo|direcci[oó]n|socios?|cliente|jefe|gerencia)"
)
EXPECTS = r"(?:expects?|wants?|needs?|is\s+counting\s+on|hopes?|espera|quiere|necesita)"
ANSWER = (
    r"(?:yes|ship|go|a\s+(?:yes|positive|significant|go)|success|approval|it\s+to\s+work|"
    r"a\s+win|s[ií]|un\s+s[ií]|que\s+funcione|un\s+resultado\s+positivo|aprobaci[oó]n)"
)
SETTLED = r"(?=\s*(?:[.;!?,]|$)|\s+(?:here|from\s+this|aqu[ií]|de\s+esto)\b)"
EXPECTATION = re.compile(
    rf"\b{EXPECTER}\b.{{0,40}}?\b{EXPECTS}\b\s+(?:to\s+see\s+)?{ANSWER}{SETTLED}", re.I
)
POLITE = r"^\s*(?:please\s+|por\s+favor,?\s+)?"
CONFIRM_THAT = re.compile(
    POLITE + r"(?:confirm|prove|demonstrate|show|confirma|demuestra|muestra)\s+(?:that|que)\s+",
    re.I,
)
CONFIRM_BARE = re.compile(
    POLITE
    + r"(?:confirm|prove|confirma|demuestra)\s+"
    + r"(?=(?:the|our|this|el|la|los|las|nuestr\w*)\b)",
    re.I,
)
SETTLED_CLAIM = re.compile(
    r"\b(?:was|is|were|are|has|have|had|did|does|will|"
    r"(?:lift|boost|rais|lower|decreas|increas|reduc|improv|help|caus|hurt|outperform|deliver|"
    r"work|succeed|driv|sav|shorten|speed|cut|beat|drove|sped|paid|pays)\w*|"
    r"fue|es|son|fueron|ha|han|funcion\w*|redu\w*|aument\w*|mejor\w*|baj\w*|acort\w*|"
    r"disminu\w*|subi\w*|ayud\w*)\b",
    re.I,
)
CLAUSE = re.compile(r"[^.;!?]+[.;!?]?")
OPEN = {"en": "Test whether ", "es": "Comprueba si "}
SPANISH = re.compile(r"^\s*(?:por\s+favor|confirma|demuestra|muestra)\b", re.I)


def _lead(clause: str) -> re.Match[str] | None:
    match = CONFIRM_THAT.match(clause)
    if match is not None:
        return match
    bare = CONFIRM_BARE.match(clause)
    return bare if bare is not None and SETTLED_CLAIM.search(clause[bare.end() :]) else None


def _opened(clause: str) -> str:
    match = _lead(clause)
    if match is None:
        return clause.strip()
    lead = OPEN["es" if SPANISH.match(clause) else "en"]
    return lead + clause[match.end() :].strip().rstrip(" ;:,.!") + "."


def open_question(question: str) -> tuple[str, list[str]]:
    """The question without its presupposed answer, and the clauses that carried it."""
    kept: list[str] = []
    loaded: list[str] = []
    for clause in (c.strip() for c in CLAUSE.findall(question)):
        if not clause:
            continue
        if EXPECTATION.search(clause):
            loaded.append(clause)
            continue
        opened = _opened(clause)
        if opened != clause:
            loaded.append(clause)
        kept.append(opened)
    if not loaded or not kept:
        return question, []
    return " ".join(kept), loaded


def loaded_caveat(question: str, opened: str, loaded: list[str]) -> str | None:
    if not loaded or opened == question:
        return None
    quoted = "; ".join(f'"{c.rstrip(" ;:,.")[:120]}"' for c in loaded[:2])
    return (
        f"The question asked for a conclusion ({quoted}). Borges planned, judged and summarised "
        f'the open question, "{opened[:200]}", so that wording could not steer the options or '
        "the verdict, which comes from the decision rule on the data."
    )
