from __future__ import annotations

from borges.analysis.narrative_failures import restate_failures
from borges.analysis.narrative_robustness import robustness_sentence
from borges.cli_render import robustness_line
from borges.garden.models import Report
from tests.garden.synthetic import result


def report(n_failed: int, basis: str = "design_weighted") -> Report:
    return Report.model_validate(
        {
            "question": "q",
            "original_verdict": "DEPENDS ON NORMS",
            "original_result": result(1.27),
            "minimal_flip": None,
            "influences": [],
            "robustness": 1.0,
            "robustness_basis": basis,
            "n_universes": 29,
            "n_attempted": 29 + n_failed,
            "n_flipped": 0,
            "n_failed": n_failed,
        }
    )


def test_the_sentence_names_failures_next_to_the_share() -> None:
    sentence = robustness_sentence(report(8))
    assert sentence is not None
    assert "100% of the analysis grid agrees" in sentence
    assert "8 more universes failed and are untested" in sentence
    assert "29 of 37 attempted completed" in sentence


def test_a_single_failure_is_singular() -> None:
    sentence = robustness_sentence(report(1, "distinct_results"))
    assert sentence is not None
    assert "1 more universe failed and is untested" in sentence


def test_no_failures_leaves_the_sentence_unchanged() -> None:
    sentence = robustness_sentence(report(0))
    assert sentence == (
        "Robustness: 100% of the analysis grid agrees with the original verdict and 0% reverses it."
    )


def test_the_cli_line_names_failures() -> None:
    line = robustness_line(report(8))
    assert "8 more failed and are untested" in line
    assert "29 of 37 attempted completed" in line


def test_the_robustness_sentence_survives_failure_restating() -> None:
    caveat = "8 universes could not run and are left out of the robustness figure: failed."
    rep = report(8).model_copy(update={"caveats": [caveat]})
    sentence = robustness_sentence(rep)
    assert sentence is not None
    assert sentence in restate_failures(rep, f"The estimate is 1.27. {sentence}")
