from __future__ import annotations

from borges.analysis.narrative_repeats import drop_prompt_echoes, drop_repeated_sentences

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


def test_a_sentence_without_figures_said_twice_is_dropped() -> None:
    text = (
        "The decision 'Filter extreme deaths' had no effect on the model and its options are "
        "excluded from the robustness share. The option 'Square-root transform deaths' was "
        "accepted. The decision 'Filter extreme deaths' had no effect and its options are "
        "excluded from the robustness share."
    )
    assert drop_repeated_sentences(text).count("Filter extreme deaths") == 1
    assert "Square-root" in drop_repeated_sentences(text)


def test_a_copied_instruction_and_its_label_are_removed() -> None:
    text = (
        "Scale of the estimate: the original analysis is a model of log1p(alldeaths). Describe "
        "every estimate on that scale. Robustness: 100% agree."
    )
    out = drop_prompt_echoes(
        text, ("Describe every estimate on that scale.",), ("Scale of the estimate: ",)
    )
    assert out == "The original analysis is a model of log1p(alldeaths). Robustness: 100% agree."


def test_a_reproduction_said_twice_in_other_words_is_dropped() -> None:
    text = (
        "An independent re-execution reproduced this flip. The covariates move the estimate. "
        "The minimal flip was reproduced by an independent re-execution."
    )
    assert drop_repeated_sentences(text) == (
        "An independent re-execution reproduced this flip. The covariates move the estimate."
    )
