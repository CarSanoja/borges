from __future__ import annotations

from collections import Counter

from borges.armor.pii_deep import redact_deep


def test_nested_structures_are_redacted_and_counted() -> None:
    counts: Counter[str] = Counter()
    value = {"a": ["x@y.com", {"b": "call +34 612 345 678"}], "n": 3, "t": ("z@w.org",)}
    out = redact_deep(value, counts)
    assert out == {
        "a": ["[redacted:email]", {"b": "call [redacted:phone]"}],
        "n": 3,
        "t": ("[redacted:email]",),
    }
    assert counts == {"email": 2, "phone": 1}
    assert value["a"][0] == "x@y.com"
