from __future__ import annotations

from borges.analysis.narrative_counts import drop_wrong_counts
from borges.garden.models import Report
from tests.garden.synthetic import result


def report(**fields: object) -> Report:
    base = {
        "question": "q",
        "original_verdict": "BIAS DETECTED",
        "original_result": result(1.23),
        "minimal_flip": None,
        "influences": [],
        "robustness": 0.83,
        "n_universes": 8,
        "n_flipped": 1,
        "n_distinct_results": 7,
        "robustness_beam": 6 / 7,
        "robustness_design": 0.83,
    }
    return Report.model_validate({**base, **fields})


def test_an_invented_count_of_universes_is_dropped() -> None:
    text = (
        "The verdict is BIAS DETECTED. Across the explored universes, the estimate ranges from "
        "1.15 to 1.33; five of eight universes (63%) retain BIAS DETECTED, while one "
        "combination reverses it. Robustness: 83% of the analysis grid agrees."
    )
    out = drop_wrong_counts(report(), text)
    assert "five of eight" not in out
    assert out == "The verdict is BIAS DETECTED. Robustness: 83% of the analysis grid agrees."


def test_true_counts_and_shares_are_kept() -> None:
    text = (
        "Seven of the eight universes retain the verdict. 6 of 7 distinct universes (86%) agree, "
        "and 1 of 8 universes flips it."
    )
    assert drop_wrong_counts(report(), text) == text
