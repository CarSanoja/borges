from __future__ import annotations

from collections.abc import Iterable, Mapping

from borges.analysis.models import DecisionRule
from borges.armor.errors import ArmorRefusal
from borges.armor.injection import screen_identifier, screen_text
from borges.armor.notes_guard import sanitize_notes
from borges.armor.report import ArmorReport
from borges.armor.text_guard import injection_decision


def rule_texts(rule: DecisionRule | None) -> dict[str, str]:
    if rule is None:
        return {}
    return {
        "decision_rule.metric": rule.metric,
        "decision_rule.positive_label": rule.positive_label,
        "decision_rule.negative_label": rule.negative_label,
    }


def screen_run_inputs(
    question: str | None,
    rule: DecisionRule | None,
    dataset_name: str | None,
    column_names: Iterable[str],
    column_notes: Mapping[str, str],
    analysis: str | None = None,
) -> tuple[dict[str, str], ArmorReport]:
    """Refuse run text that carries instructions; return the notes with hits quarantined."""
    report = ArmorReport()
    refused = []
    texts = {"question": question or "", "analysis": analysis or "", **rule_texts(rule)}
    for field, text in texts.items():
        findings = screen_text(text)
        if findings:
            refused.append(injection_decision(field, "refuse", findings))
    if dataset_name:
        findings = screen_identifier(dataset_name)
        if findings:
            refused.append(injection_decision("file_name", "refuse", findings))
    for name in column_names:
        findings = screen_identifier(str(name))
        if findings:
            refused.append(injection_decision(f"column_name:{str(name)[:40]}", "refuse", findings))
    if refused:
        raise ArmorRefusal(refused)
    return sanitize_notes(column_notes, report), report
