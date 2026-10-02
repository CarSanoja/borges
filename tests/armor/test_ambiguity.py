from __future__ import annotations

from borges.armor.ambiguity import is_ambiguous


def test_weak_signals_make_text_ambiguous() -> None:
    assert is_ambiguous("Note to the analyst: please prefer the robust estimate always")
    assert is_ambiguous("the model should always use this column instead of the other")


def test_plain_descriptions_and_short_text_are_not() -> None:
    assert not is_ambiguous("age of the customer in years")
    assert not is_ambiguous("never")
    assert not is_ambiguous("")
