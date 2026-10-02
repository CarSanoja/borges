from __future__ import annotations

from borges.armor.findings import Finding
from borges.armor.injection import UNTRUSTED_INPUT, ScreenProfile, screen_text
from borges.armor.pii import count_pii, redact_pii
from borges.armor.report import QUARANTINE_TOKEN, Action, ArmorDecision, ArmorReport

AMBIGUOUS_FIELD = "text"


def summarise(findings: list[Finding]) -> tuple[str, str]:
    categories = sorted({f.category for f in findings})
    techniques = sorted({f.technique for f in findings if f.technique != "plain"})
    detail = ", ".join(categories[:4])
    if techniques:
        detail = f"{detail}; obfuscation: {', '.join(techniques)}"
    return detail, findings[0].quote


def injection_decision(field: str, action: Action, findings: list[Finding]) -> ArmorDecision:
    detail, quote = summarise(findings)
    return ArmorDecision(action, "injection", field, detail, len(findings), quote)


def pii_decisions(field: str, text: str, column: str | None = None) -> list[ArmorDecision]:
    return [
        ArmorDecision("redact", "pii", field, kind, count)
        for kind, count in sorted(count_pii(text, column).items())
    ]


def sanitize_value(
    field: str,
    text: str,
    report: ArmorReport,
    column: str | None = None,
    profile: ScreenProfile = UNTRUSTED_INPUT,
) -> str:
    """Quarantine instruction-like text, otherwise redact personal data; record each decision."""
    findings = screen_text(text, profile)
    if findings:
        report.add(injection_decision(field, "quarantine", findings))
        return QUARANTINE_TOKEN
    decisions = pii_decisions(field, text, column)
    for decision in decisions:
        report.add(decision)
    return redact_pii(text, column) if decisions else text
