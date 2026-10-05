from __future__ import annotations

from borges.analysis.narrative_repeats import drop_repeated_sentences

STORY = (
    "The analysis explored 8 distinct modeling universes via an independent design, finding that "
    "64% of explored universes flipped the conclusion, though this sample leans toward flips. "
    "The independent design found 64% of 8 distinct universes flipped the conclusion. "
    "The minimal flip changes the model."
)


def test_a_sentence_that_restates_the_same_figures_is_dropped() -> None:
    kept = drop_repeated_sentences(STORY)
    assert "The independent design found" not in kept
    assert kept.startswith("The analysis explored 8") and kept.endswith("changes the model.")


def test_sentences_with_different_figures_or_words_are_kept() -> None:
    story = (
        "The baseline gives 0.12 with n 500. The flip gives 0.03 with n 500. It moved 0.12 away."
    )
    assert drop_repeated_sentences(story) == story


def test_a_figure_restated_inside_its_own_parenthesis_is_collapsed() -> None:
    text = (
        "The original analysis found a lift of 0.53 percentage points (0.53 percentage points "
        "(95% CI 0.14 to 0.92, p = 0.008) and returned SHIP."
    )
    assert drop_repeated_sentences(text) == (
        "The original analysis found a lift of 0.53 percentage points (95% CI 0.14 to 0.92, "
        "p = 0.008) and returned SHIP."
    )
    plain = "An odds ratio of 1.33 (95% CI 1.13 to 1.56) for darker players (n = 124621)."
    assert drop_repeated_sentences(plain) == plain
