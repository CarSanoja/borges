from __future__ import annotations

from borges.armor.pii_fold import fold_with_map


def test_zero_width_and_bidi_characters_are_dropped_with_a_map() -> None:
    folded, origin = fold_with_map("a​b‮c")
    assert folded == "abc" and origin == [0, 2, 4]


def test_unicode_spaces_become_plain_spaces_and_fullwidth_is_folded() -> None:
    folded, origin = fold_with_map("4 5ＡＢ")
    assert folded == "4 5AB" and origin == [0, 1, 2, 3, 4]


def test_newlines_and_tabs_survive() -> None:
    assert fold_with_map("a\nb\tc")[0] == "a\nb\tc"


def test_expansions_map_back_to_their_source_character() -> None:
    folded, origin = fold_with_map("ﬁx")
    assert folded == "fix" and origin == [0, 0, 1]
