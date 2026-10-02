from __future__ import annotations

from borges.armor.normalize import (
    TECHNIQUE_BASE64,
    TECHNIQUE_LEET,
    TECHNIQUE_REVERSED,
    TECHNIQUE_ROT13,
    TECHNIQUE_SPACED,
    canonical,
    deleet,
    fold_homoglyphs,
    has_confusables,
    normalize_identifier,
    strip_invisible,
    variants_of,
)


def test_invisible_and_bidi_controls_are_stripped() -> None:
    assert strip_invisible("ig​no‮re⁠") == "ignore"
    assert strip_invisible("a\nb\tc") == "a\nb\tc"


def test_nfkc_folds_fullwidth_and_homoglyphs_fold_lookalikes() -> None:
    assert fold_homoglyphs("ＳＨＩＰ") == "SHIP"
    assert fold_homoglyphs("ignоrе") == "ignore"


def test_canonical_is_lowercase_accentless() -> None:
    assert canonical("ÍGNÓRA Ñu") == "ignora nu"


def test_confusable_detection() -> None:
    assert has_confusables("ignоre") and has_confusables("a​b")
    assert not has_confusables("plain text\n")


def test_deleet_and_identifier_normalisation() -> None:
    assert deleet("1gn0r3") == "ignore"
    assert normalize_identifier("systemNoteConcludeShip") == "system note conclude ship"
    assert normalize_identifier("ignore_the_rule") == "ignore the rule"


def test_variants_cover_each_obfuscation() -> None:
    techniques = {v.technique for v in variants_of("1gn0r3 vtaber ZW9yZGVyIHJlcG9ydCBzaGlwIQ==")}
    assert {TECHNIQUE_LEET, TECHNIQUE_REVERSED, TECHNIQUE_ROT13, TECHNIQUE_BASE64} <= techniques
    assert TECHNIQUE_SPACED in {v.technique for v in variants_of("i g n o r e")}


def test_variants_are_distinct() -> None:
    texts = [v.text for v in variants_of("hello")]
    assert len(texts) == len(set(texts))
