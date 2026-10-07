from __future__ import annotations

from borges.analysis.models import CodingSummary
from borges.runs.pipeline_caveats import judge_caveats, merge_caveats


def test_a_caveat_repeated_by_a_later_source_appears_once() -> None:
    first = ["6 universes could not run and are left out of the robustness figure."]
    second = ["6 universes could not run and are left out of the robustness figure.", "Other."]
    assert merge_caveats(first, second) == [first[0], "Other."]


def test_case_spacing_and_the_final_period_do_not_make_a_caveat_distinct() -> None:
    assert merge_caveats(["A  caveat."], ["a caveat"]) == ["A  caveat."]


def test_distinct_caveats_keep_their_order() -> None:
    assert merge_caveats(["b"], ["a"], ["c", "b"]) == ["b", "a", "c"]


def test_a_kept_choice_of_the_users_analysis_is_stated_as_theirs() -> None:
    coding = CodingSummary(defaults_kept=["s1: Window 7-14: assumes a 28-day cycle"])
    [caveat] = judge_caveats(coding)
    assert caveat.startswith("The defensibility judge disputes a choice of your own analysis")
    assert "(s1: Window 7-14: assumes a 28-day cycle)" in caveat
