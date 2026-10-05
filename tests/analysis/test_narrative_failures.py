from __future__ import annotations

from borges.analysis.narrative_failures import restate_failures
from borges.garden.models import Report
from tests.garden.synthetic import result

CAVEAT = (
    "3 universes could not run and are left out of the robustness figure: failed 2 in 'Logit' "
    "(LinAlgError: Singular matrix); 1 in 'Poisson' (the process was stopped, exit code -1)."
)


def report(caveats: list[str]) -> Report:
    return Report.model_validate(
        {
            "question": "q",
            "original_verdict": "BIAS",
            "original_result": result(1.27),
            "minimal_flip": None,
            "influences": [],
            "robustness": 1.0,
            "n_universes": 8,
            "n_flipped": 0,
            "caveats": caveats,
        }
    )


def test_a_summary_sentence_about_failed_universes_becomes_the_caveat() -> None:
    text = (
        "The original analysis estimated 1.27. Three universes failed due to singular-matrix "
        "errors, and are excluded. Robustness: 100%."
    )
    out = restate_failures(report([CAVEAT]), text)
    assert out == f"The original analysis estimated 1.27. {CAVEAT} Robustness: 100%."


def test_other_failures_are_not_universe_failures() -> None:
    text = "Excluding respondents who failed the attention check gives 0.09. All 24 universes ran."
    assert restate_failures(report([CAVEAT]), text) == text
    assert restate_failures(report([]), "Two universes failed.") == "Two universes failed."
