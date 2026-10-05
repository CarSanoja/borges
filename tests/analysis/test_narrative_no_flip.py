from __future__ import annotations

from borges.analysis.narrative_no_flip import (
    claimed_flips,
    no_flip_problems,
    rewrite_claimed_flips,
)
from borges.analysis.narrative_robustness import robustness_sentence
from borges.garden.models import Change, Flip, Report
from tests.garden.synthetic import result

CLAIM = (
    "The original analysis estimated -0.128. A minimal flip was found: excluding only bots gives "
    "SHIP. However, the flip is contaminated."
)


def report(contaminated: bool) -> Report:
    flip = Flip(
        universe_id="u_x",
        changes=[
            Change(
                step_id="rows",
                step_title="Rows",
                from_option="both",
                to_option="bots",
                to_label="Exclude only bots",
                rationale="r",
            )
        ],
        baseline_result=result(-0.128, p=0.49),
        flipped_result=result(0.576, p=0.0097),
        baseline_verdict="DON'T SHIP",
        flipped_verdict="SHIP",
        contaminated=True,
    )
    return Report.model_validate(
        {
            "question": "q",
            "original_verdict": "DON'T SHIP",
            "original_result": result(-0.128, p=0.49),
            "minimal_flip": None,
            "influences": [],
            "robustness": 1.0,
            "robustness_basis": "design_weighted",
            "n_universes": 18,
            "n_flipped": 6,
            "contaminated_flips": [flip] if contaminated else [],
        }
    )


def test_a_minimal_flip_claimed_beside_a_contaminated_one_is_rewritten() -> None:
    assert len(no_flip_problems(report(True), CLAIM)) == 1
    out = rewrite_claimed_flips(report(True), CLAIM)
    assert "A minimal flip was found" not in out
    assert "The only flip found is contaminated: excluding only bots gives SHIP." in out


def test_a_minimal_flip_claimed_with_no_flip_at_all_is_dropped() -> None:
    out = rewrite_claimed_flips(report(False), CLAIM)
    assert out == "The original analysis estimated -0.128. However, the flip is contaminated."


def test_a_no_flip_sentence_is_not_a_claim() -> None:
    assert claimed_flips(report(True), "No minimal flip was found.") == []


def test_the_robustness_sentence_says_invalid_rows_are_left_out() -> None:
    sentence = robustness_sentence(report(True))
    assert sentence is not None
    assert "0% reverses it, leaving out the universes that re-include rows" in sentence
    assert robustness_sentence(report(False)).endswith("0% reverses it.")


def test_report_field_echoes_are_dropped() -> None:
    text = (
        "No change reversed this verdict; the minimal flip is null. Because no flip was found, "
        "there is no re-execution to report. Robustness: 100%."
    )
    assert rewrite_claimed_flips(report(False), text) == (
        "No change reversed this verdict. Robustness: 100%."
    )


def test_an_absent_minimal_flip_is_dropped() -> None:
    text = "The search found no change that reversed the verdict; the minimal flip is absent."
    assert rewrite_claimed_flips(report(False), text) == (
        "The search found no change that reversed the verdict."
    )
