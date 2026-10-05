from __future__ import annotations

from borges.analysis.models import AnalysisResult
from borges.analysis.narrative_flip import flipped_sentence, with_flipped
from tests.analysis.test_narrative_flip import checkout_report

FLIPPED = AnalysisResult(estimate=3.378, ci_low=0.42, ci_high=6.33, p_value=0.024, n=93)
FLIP_SENTENCE = 'The minimal flip changes Model from "OLS" to "Negative binomial".'


def report():
    base = checkout_report()
    assert base.minimal_flip is not None
    flip = base.minimal_flip.model_copy(update={"flipped_result": FLIPPED})
    return base.model_copy(update={"minimal_flip": flip})


def test_a_narrative_without_the_flipped_estimate_gets_it_after_the_flip() -> None:
    text = f"Opening. {FLIP_SENTENCE} The flipped result exceeds the mean. Robustness: 88%."
    stated = flipped_sentence(report())
    assert stated is not None and "3.38 (95% CI 0.42 to 6.33, p = 0.024, n = 93)" in stated
    assert f"{FLIP_SENTENCE} {stated} The flipped result" in with_flipped(
        report(), text, FLIP_SENTENCE
    )


def test_a_narrative_that_gives_the_flipped_estimate_is_kept() -> None:
    text = f"Opening. {FLIP_SENTENCE} The flipped universe estimates 3.38 deaths."
    assert with_flipped(report(), text, FLIP_SENTENCE) == text
