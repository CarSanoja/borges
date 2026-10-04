from __future__ import annotations

from borges.analysis.narrative_repeats import drop_repeated_sentences, restates_any

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


def test_a_narrated_caveat_that_restates_a_deterministic_one_is_recognised() -> None:
    deterministic = [
        "20 universes ran but only 15 gave distinct results; universes with identical results "
        "are counted once in the robustness share.",
        "The option 'NB without clustering' (m) duplicates 'NB clustered' (planner option).",
    ]
    restated = "Only 15 of 20 universes yielded distinct results; identical-result universes are "
    restated += "counted once in the robustness share."
    assert restates_any(restated, deterministic)
    assert restates_any(
        "The option 'NB without clustering' duplicates the planner's NB.", deterministic
    )


def test_a_caveat_about_another_option_or_new_facts_is_kept() -> None:
    deterministic = [
        "The option 'Psychological mean' (wb) is a no-op: same result as the baseline."
    ]
    assert not restates_any(
        "The option 'Social mean' (wb) is a no-op: same result as the baseline.", deterministic
    )
    assert not restates_any(
        "Two universes failed because the column 'day' was missing.", deterministic
    )
