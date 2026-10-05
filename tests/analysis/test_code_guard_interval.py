from __future__ import annotations

from borges.analysis.code_guard_interval import interval_level_violations


def test_a_97_5_percent_interval_is_flagged() -> None:
    found = interval_level_violations("ci = res.conf_int(alpha=0.025).loc['x']\n")
    assert len(found) == 1 and "97.5% interval" in found[0]
    assert interval_level_violations("ci = res.conf_int(0.1)\n")


def test_a_95_percent_interval_passes() -> None:
    assert interval_level_violations("ci = res.conf_int()\nlow = res.conf_int(alpha=0.05)\n") == []
    assert interval_level_violations("frame = pred.summary_frame(alpha=0.05)\n") == []
