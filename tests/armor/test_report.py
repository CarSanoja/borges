from __future__ import annotations

from borges.armor.report import ArmorDecision, ArmorReport


def test_caveats_summarise_each_action() -> None:
    report = ArmorReport()
    report.add(ArmorDecision("quarantine", "injection", "column_note:age", "override"))
    report.add(ArmorDecision("redact", "pii", "sample_value:mail", "email", 3))
    report.add(ArmorDecision("drop", "tool_poisoning", "adversary:s.o", "steering"))
    lines = report.caveats()
    assert len(lines) == 3
    assert "quarantined 1" in lines[0] and "column_note:age" in lines[0]
    assert "email x3" in lines[1]
    assert "dropped 1" in lines[2]


def test_empty_report_is_falsy_and_extend_merges() -> None:
    report = ArmorReport()
    assert not report and report.caveats() == []
    other = ArmorReport([ArmorDecision("redact", "pii", "f", "email")])
    report.extend(other)
    assert report and report.pii_counts() == {"email": 1}
    assert not ArmorDecision("redact", "pii", "f", "email").denies
    assert ArmorDecision("refuse", "injection", "f", "x").denies


def test_remembered_entries_kept_out_are_not_called_options_of_this_run() -> None:
    report = ArmorReport()
    report.add(ArmorDecision("drop", "tool_poisoning", "memory:option:ab12cd34", "steering"))
    report.add(ArmorDecision("drop", "tool_poisoning", "memory:option:ef56ab78", "steering"))
    [line] = report.caveats()
    assert line.startswith("Armor kept 2 remembered entries from earlier runs")
    assert "model-proposed option" not in line
