from __future__ import annotations

from borges.analysis.models import AnalysisResult
from borges.analysis.narrative_robustness import (
    drop_inverted_sentences,
    robustness_problems,
    robustness_sentence,
)
from borges.garden.models import Report


def report() -> Report:
    result = AnalysisResult(estimate=1.09, ci_low=0.98, ci_high=1.2, p_value=0.099, n=126793)
    return Report(
        question="Q?",
        original_verdict="NO CLEAR EVIDENCE",
        original_result=result,
        minimal_flip=None,
        influences=[],
        robustness=0.6,
        n_universes=15,
        n_flipped=4,
        robustness_basis="design_weighted",
        robustness_beam=0.6923,
        robustness_design=0.6,
    )


INVERTED = (
    "The analysis examined skin tone and red cards. 69% of the explored universes flipped the "
    "conclusion. Across the grid the conclusion flipped in a majority."
)


def test_the_sentence_states_the_agreeing_share_and_its_complement() -> None:
    assert robustness_sentence(report()) == (
        "Robustness: 60% of the analysis grid agrees with the original verdict and 40% reverses it."
    )


def test_an_agreeing_share_read_as_flips_is_rejected_and_dropped() -> None:
    found = robustness_problems(report(), INVERTED)
    assert "it says 69% reverse the verdict, but 69% is the share that agrees with it" in found
    assert any(p.startswith("the robustness sentence is missing") for p in found)
    kept = drop_inverted_sentences(report(), INVERTED)
    assert "69%" not in kept and kept.startswith("The analysis examined")


def test_a_correct_narrative_passes() -> None:
    text = f"The verdict holds. {robustness_sentence(report())} 31% of explored universes flip."
    assert robustness_problems(report(), text) == []
