from __future__ import annotations

from borges.analysis.narrative_measure import name_original_measure

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
