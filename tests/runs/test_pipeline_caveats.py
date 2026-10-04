from __future__ import annotations

from borges.runs.pipeline_caveats import merge_caveats


def test_a_caveat_repeated_by_a_later_source_appears_once() -> None:
    first = ["6 universes could not run and are left out of the robustness figure."]
    second = ["6 universes could not run and are left out of the robustness figure.", "Other."]
    assert merge_caveats(first, second) == [first[0], "Other."]


def test_case_spacing_and_the_final_period_do_not_make_a_caveat_distinct() -> None:
    assert merge_caveats(["A  caveat."], ["a caveat"]) == ["A  caveat."]


def test_distinct_caveats_keep_their_order() -> None:
    assert merge_caveats(["b"], ["a"], ["c", "b"]) == ["b", "a", "c"]
