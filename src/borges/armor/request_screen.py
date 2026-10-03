from __future__ import annotations

from collections.abc import Mapping

from borges.analysis.models import DecisionRule
from borges.armor.errors import ArmorRefusal
from borges.armor.injection import screen_text
from borges.armor.report import ArmorDecision
from borges.armor.run_inputs import rule_texts
from borges.armor.text_guard import injection_decision

MAX_NOTE_CHARS = 500


def screen_request_text(
    question: str | None,
    rule: DecisionRule | None,
    column_notes: Mapping[str, str] | None,
) -> list[ArmorDecision]:
    texts = {"question": question or "", **rule_texts(rule)}
    for name, note in (column_notes or {}).items():
        texts[f"column_note:{str(name)[:40]}"] = str(note)[:MAX_NOTE_CHARS]
    decisions: list[ArmorDecision] = []
    for field, text in texts.items():
        findings = screen_text(text)
        if findings:
            decisions.append(injection_decision(field, "refuse", findings))
    return decisions


def refuse_injected_request(
    question: str | None,
    rule: DecisionRule | None,
    column_notes: Mapping[str, str] | None,
) -> None:
    decisions = screen_request_text(question, rule, column_notes)
    if decisions:
        raise ArmorRefusal(decisions)
