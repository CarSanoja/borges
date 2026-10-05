from __future__ import annotations

from borges.analysis.narrative_measure import name_every_measure, name_original_measure

OPENING = (
    "The original analysis estimated an odds ratio of 1.14 (95% CI 1.02 to 1.28, p = 0.022), "
    "yielding BIAS DETECTED."
)


def test_the_original_estimate_is_named_by_the_measure_fitted() -> None:
    out = name_original_measure(OPENING, "rate ratio")
    assert out.startswith("The original analysis estimated a rate ratio of 1.14")


def test_other_clauses_and_matching_names_are_left_alone() -> None:
    mixed = (
        "The original analysis estimated 1.27, while the Poisson option gives a rate ratio of "
        "1.22. A logit gives an odds ratio of 1.3."
    )
    assert name_original_measure(mixed, "odds ratio") == mixed
    assert name_original_measure(OPENING, "odds ratio") == OPENING
    assert name_original_measure(OPENING, None) == OPENING


def test_every_ratio_is_named_as_the_one_measure_the_run_reports() -> None:
    text = (
        "The original analysis estimated 1.15. Adjusting for demographics moved the odds ratio "
        "to 1.15. The decision rule is stated as an odds ratio above 1."
    )
    assert name_every_measure(text, "rate ratio") == (
        "The original analysis estimated 1.15. Adjusting for demographics moved the rate ratio "
        "to 1.15. The decision rule is stated as an odds ratio above 1."
    )
    assert name_every_measure(text, None) == text


def test_a_sentence_that_contrasts_two_measures_is_kept() -> None:
    text = "The judge rejected Poisson regression as estimating a rate ratio, not an odds ratio."
    assert name_every_measure(text, "odds ratio") == text
