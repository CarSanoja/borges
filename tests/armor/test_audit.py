from __future__ import annotations

from borges.armor.audit import record_decision, record_report
from borges.armor.report import ARMOR_PRINCIPAL, ArmorDecision, ArmorReport


def test_denials_and_redactions_get_the_right_decision_and_no_pii() -> None:
    seen: list[tuple[str, dict]] = []

    def sink(kind: str, **fields) -> None:
        seen.append((kind, fields))

    report = ArmorReport(
        [
            ArmorDecision("refuse", "injection", "question", "override", 1, "ignore x@y.com"),
            ArmorDecision("redact", "pii", "prompt", "email", 2),
        ]
    )
    record_report(report, sink, stage="t")
    assert [k for k, _ in seen] == ["armor.screen", "armor.screen"]
    assert seen[0][1]["decision"] == "deny" and seen[1][1]["decision"] == "observe"
    assert seen[0][1]["principal"] == ARMOR_PRINCIPAL and seen[0][1]["stage"] == "t"
    assert "x@y.com" not in seen[0][1]["reason"]
    record_decision(report.decisions[1], sink, "agent://borges/judge")
    assert seen[2][1]["principal"] == "agent://borges/judge"
