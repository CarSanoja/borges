from __future__ import annotations

from borges.analysis.models import AnalysisResult
from borges.analysis.narrative_original import (
    original_problems,
    original_sentence,
    with_original,
)
from borges.garden.models import Report
from tests.analysis.fakes import make_plan


def report() -> Report:
    result = AnalysisResult(estimate=0.0372, ci_low=0.0203, ci_high=0.0541, p_value=1.6e-5, n=10503)
    return Report(
        question="Do norms moderate it?",
        original_verdict="DEPENDS ON NORMS",
        original_result=result,
        minimal_flip=None,
        influences=[],
        robustness=1.0,
        n_universes=29,
        n_flipped=0,
    )


WRONG = (
    "The analysis examined 10,170 respondents. The primary estimand was an interaction "
    "(beta = 0.024, 95% CI [0.005, 0.044], p = 0.015). A pre-registered adversary proposed two "
    "alternative specifications. Both kept the verdict."
)


def test_the_original_sentence_comes_from_the_report() -> None:
    assert original_sentence(report()) == (
        "The original analysis estimated 0.0372 (95% CI 0.0203 to 0.0541, p < 0.001, "
        "n = 10,503) and returned the verdict DEPENDS ON NORMS."
    )


def test_another_universe_told_as_the_original_and_an_invented_adversary_are_problems() -> None:
    found = original_problems(make_plan(), report(), WRONG)
    assert found[0].startswith("it states the original analysis with numbers it does not have")
    assert "0.024" in found[0]
    assert "no adversary option entered the garden" in found[1]


def test_the_original_in_the_narrator_s_words_and_rounding_is_accepted() -> None:
    text = (
        "The original analysis found an interaction of 0.037 (95% CI 0.02 to 0.054, n = 10,503) "
        "and the verdict DEPENDS ON NORMS. Both kept the verdict."
    )
    assert original_problems(make_plan(), report(), text) == []
    assert with_original(make_plan(), report(), text) == text


def test_the_fallback_states_the_original_and_drops_what_contradicts_it() -> None:
    fixed = with_original(make_plan(), report(), WRONG)
    assert fixed == (
        f"{original_sentence(report())} The analysis examined 10,170 respondents. "
        "Both kept the verdict."
    )


def test_an_opening_with_the_estimate_rounded_to_a_whole_number_is_not_repeated() -> None:
    gap = AnalysisResult(estimate=-502.856, ci_low=-1197.4, ci_high=191.7, p_value=0.156, n=1500)
    pay = report().model_copy(
        update={"original_result": gap, "original_verdict": "NO SIGNIFICANT GAP"}
    )
    narrative = (
        "The original analysis estimated -503 (95% CI -1.2e+03 to 192, p = 0.16, n = 1,500) and "
        "returned the verdict NO SIGNIFICANT GAP. No change flips it."
    )
    assert with_original(make_plan(), pay, narrative) == narrative
