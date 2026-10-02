from __future__ import annotations

from borges.armor.findings import Finding, clip


def test_clip_flattens_whitespace_and_truncates() -> None:
    assert clip("a\n  b") == "a b"
    assert len(clip("x" * 200)) == 60 and clip("x" * 200).endswith("…")


def test_finding_describes_category_and_technique() -> None:
    assert Finding("override.x", "override.x", "base64", "q").describe() == "override.x (base64)"
